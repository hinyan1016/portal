"""記事カード用の画像を、ブログのアイキャッチ（本文の先頭画像。多くはインフォグラフィック）から作る。

図解マニフェストの blog_url が記事と一致しないと、記事カードに画像が付かなかった（2026-10-21 時点で
1,337件中159件）。ブログのアーカイブ一覧には各記事のアイキャッチが載っているので、その元画像の上部を
16:9で切り出し、幅640pxのWebPにして thumbs/articles/<記事の日時>.webp に置く。

- 対応表は scripts/article_images.json（記事URL → 元画像URLとサムネイル）。元画像が同じなら作り直さない。
- アイキャッチが診断支援ツールの図解なら、図解カード用の thumbs/<slug>.webp をそのまま使う。
- 定期実行では一覧の1ページ目（新着）と、巡回中の1ページだけを読む。全ページで約2週間に1周する。
  導入時と取りこぼしの修復は --all で全ページを読む。
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.build_thumbs import fit_top  # noqa: E402

BLOG = 'https://blog.ichisouzo-lab.com'
TOOLS_HOST = 'tools.ichisouzo-lab.com'
OUT = ROOT / 'thumbs' / 'articles'
MAP_PATH = ROOT / 'scripts' / 'article_images.json'
WIDTH, HEIGHT = 640, 360
ENTRY = re.compile(re.escape(BLOG) + r'/entry/(\d{4})/(\d{2})/(\d{2})/(\d{6})')
# 元画像として取得してよいホスト。それ以外はアイキャッチの縮小版（はてなの署名付きURL）を使う。
SOURCE_HOSTS = {'cdn-ak.f.st-hatena.com', TOOLS_HOST}
HEADERS = {'User-Agent': 'IchisouzoThumbs/1.0'}


def fetch(url, binary=False):
    with urlopen(Request(url, headers=HEADERS), timeout=60) as response:
        data = response.read()
    return data if binary else data.decode('utf-8')


def thumb_key(url):
    y, mo, d, hms = ENTRY.fullmatch(url).groups()
    return f'{y}{mo}{d}-{hms}'


def archive_entries(html):
    """アーカイブ1ページから (記事URL, アイキャッチURL or '') と次ページの有無を返す。"""
    out = []
    for section in re.findall(r'<section class="archive-entry\b.*?</section>', html, re.S):
        link = re.search(r'class="entry-title-link[^"]*" href="([^"]+)"', section)
        if not link or not ENTRY.fullmatch(link.group(1)):
            continue
        thumb = re.search(r'class="entry-thumb"[^>]*background-image:\s*url\(\'?([^\')]+)', section)
        out.append((link.group(1), thumb.group(1) if thumb else ''))
    return out, 'rel="next"' in html


def source_url(eyecatch):
    """はてなの縮小URLの末尾に埋め込まれた元画像URLを取り出す。許可したホストでなければ縮小URLのまま。"""
    match = re.match(r'https://cdn\.image\.st-hatena\.com/image/[a-z]+/[0-9a-f]+/[^/]+/(https%3A%2F%2F.+)$', eyecatch)
    if match:
        original = unquote(match.group(1))
        if urlsplit(original).netloc in SOURCE_HOSTS:
            return original
    return eyecatch if urlsplit(eyecatch).netloc in SOURCE_HOSTS | {'cdn.image.st-hatena.com'} else ''


def infographic_slug(src):
    match = re.fullmatch(r'https://' + re.escape(TOOLS_HOST) + r'/infographics/([A-Za-z0-9_-]+)/[^/]+\.(?:png|jpe?g|webp)', src)
    return match.group(1) if match else ''


def card_image(data):
    buffer = io.BytesIO()
    fit_top(data, WIDTH, HEIGHT).save(buffer, 'WEBP', quality=75, method=6)
    return buffer.getvalue()


def plan(entries, mapping):
    """作り直しが要る記事だけを返す。元画像が同じでサムネイルがあれば何もしない。"""
    todo = []
    for url, eyecatch in entries:
        src = source_url(eyecatch) if eyecatch else ''
        known = mapping.get(url, {})
        slug = infographic_slug(src)
        if slug and (ROOT / 'thumbs' / f'{slug}.webp').exists():
            mapping[url] = {'src': src, 'img': f'thumbs/{slug}.webp'}
            continue
        if not src:
            mapping[url] = {'src': '', 'img': ''}
            continue
        target = f'thumbs/articles/{thumb_key(url)}.webp'
        if known.get('src') == src and known.get('img') == target and (ROOT / target).exists():
            continue
        todo.append((url, src, target))
    return todo


def make(job):
    url, src, target = job
    (ROOT / target).write_bytes(card_image(fetch(src, binary=True)))
    return url, src, target


def prune(mapping, keep_urls):
    """公開一覧から消えた記事の対応とサムネイルを外す。"""
    for url in [u for u in mapping if u not in keep_urls]:
        mapping.pop(url)
    used = {m['img'] for m in mapping.values() if m.get('img', '').startswith('thumbs/articles/')}
    for path in OUT.glob('*.webp'):
        if f'thumbs/articles/{path.name}' not in used:
            path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true', help='アーカイブ全ページを読む（導入時・修復用）')
    parser.add_argument('--sleep', type=float, default=2.0, help='アーカイブのページ取得の間隔（秒）')
    parser.add_argument('--workers', type=int, choices=range(1, 7), default=4)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(MAP_PATH.read_text(encoding='utf-8')) if MAP_PATH.exists() else {}
    mapping, cursor = data.get('articles', {}), data.get('cursor', 2)

    def page(n):
        html = fetch(BLOG + '/archive' + (f'?page={n}' if n > 1 else ''))
        return archive_entries(html)

    entries, seen_pages = [], []
    if args.all:
        n, more = 1, True
        while more:
            rows, more = page(n)
            entries += rows
            seen_pages.append(n)
            n += 1
            if more:
                time.sleep(args.sleep)
        cursor = 2
    else:
        rows, _ = page(1)
        entries += rows
        time.sleep(args.sleep)
        rows, more = page(cursor)
        entries += rows
        seen_pages = [1, cursor]
        cursor = cursor + 1 if more and rows else 2
    if not entries:
        raise RuntimeError('アーカイブから記事を読めません。既存の対応表を保持します。')

    todo = plan(entries, mapping)
    failed = []

    def task(job):
        try:
            return make(job)
        except Exception as error:  # 画像1枚の失敗で全体を止めない。次回に再試行する。
            failed.append(f'{job[0]}: {error}')
            return None

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(task, todo):
            if result:
                url, src, target = result
                mapping[url] = {'src': src, 'img': target}

    if args.all:
        prune(mapping, {url for url, _ in entries})
    else:
        index = json.loads((ROOT / 'search-index.json').read_text(encoding='utf-8'))
        prune(mapping, {r['u'] for r in index if r.get('k') == '記事'} | {url for url, _ in entries})
    ordered = dict(sorted(mapping.items(), reverse=True))
    MAP_PATH.write_text(json.dumps({'cursor': cursor, 'articles': ordered}, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8', newline='\n')
    with_img = sum(1 for m in ordered.values() if m.get('img'))
    size = sum(p.stat().st_size for p in OUT.glob('*.webp'))
    print(f'Article images: pages={seen_pages}, entries={len(entries)}, made={len(todo) - len(failed)}, '
          f'failed={len(failed)}, mapped={len(ordered)}, with_image={with_img}, articles_dir={size // 1024}KB')
    for line in failed[:20]:
        print('  failed', line)


if __name__ == '__main__':
    main()
