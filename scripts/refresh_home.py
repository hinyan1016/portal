"""トップの自動更新枠のデータを公開情報だけから作る。PICK UP と制作こぼれ話は対象外（手で選ぶ）。

- 医学の新着: ブログRSSのうち医学カテゴリーの最新記事。動画はチャンネルの公開フィードで
  公開を確かめた ID だけリンクする（限定公開の動画をトップから広めない）。
- 最近更新した記事: サイトマップの lastmod で候補を絞り、公開本文に日付付きの改訂告知
  （「2026年10月15日更新：」「改訂日：2026年10月20日」など）がある記事だけを台帳に足す。
  lastmod だけでは登録しない（カテゴリー変更や再保存を改訂として扱わない）。
- 実用ツールの近道: ツール一覧と配布資料マニフェストで初めて見た日を記録し、新しい順に出す。
- オフライン版: GitHub の最新リリース（offline-v*）の版・日付・ZIP・収録件数。

枠ごとに取得・検証し、失敗した枠は前回のデータを残す。書き込みは全枠の処理後に1回だけ行う。
"""
import argparse
from datetime import date, datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from article_updates import validate as validate_updates  # noqa: E402
from home_sections import apply as apply_sections  # noqa: E402
from scripts.refresh_catalog import ToolParser, clean_text  # noqa: E402

JST = timezone(timedelta(hours=9))
BLOG = 'https://blog.ichisouzo-lab.com'
TOOLS = 'https://tools.ichisouzo-lab.com'
CHANNEL_FEED = 'https://www.youtube.com/feeds/videos.xml?channel_id=UCmZ9m9j2T9isCuJpsoiY9qQ'
RELEASES_API = 'https://api.github.com/repos/hinyan1016/medical-ddx-tools/releases?per_page=20'
FEED_PATH, STATE_PATH, CONFIG_PATH = ROOT / 'home-feed.json', ROOT / 'scripts' / 'home_state.json', ROOT / 'home-config.json'
UPDATES_PATH = ROOT / 'article-updates.json'
ENTRY_RE = re.compile(re.escape(BLOG) + r'/entry/(\d{4})/(\d{2})/(\d{2})/\d{6}')
EMBED_RE = re.compile(r'youtube(?:-nocookie)?\.com/embed/([\w-]{11})')
BLOCK_TAGS = {'p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'tr', 'td', 'th',
              'section', 'article', 'details', 'summary', 'figcaption', 'blockquote', 'aside', 'dt', 'dd', 'table'}


def today_jst():
    return datetime.now(JST).date()


def fetch(url, accept=''):
    headers = {'User-Agent': 'IchisouzoHome/1.0'}
    if accept:
        headers['Accept'] = accept
    token = os.environ.get('GITHUB_TOKEN', '')
    if token and url.startswith('https://api.github.com/'):
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return response.read().decode('utf-8')


class BlockText(HTMLParser):
    """本文をブロック単位の行に分けた文字列にする。script/style は読まない。"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
        elif tag in BLOCK_TAGS:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK_TAGS:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def lines(self):
        return [re.sub(r'\s+', ' ', line).strip() for line in ''.join(self.parts).split('\n') if line.strip()]


def block_lines(html):
    parser = BlockText()
    parser.feed(html)
    parser.close()
    return parser.lines()


# ---- 医学の新着 --------------------------------------------------------------

def split_title(title):
    """末尾の【医師向け】などを外し、「〜向け」なら読者表示として返す。"""
    title = clean_text(title)
    label = ''
    match = re.search(r'\s*【([^】]{1,12})】\s*$', title)
    if match:
        title = title[:match.start()].strip()
        if match.group(1).endswith('向け'):
            label = match.group(1)
    return title, label


def shorten(text, limit=90):
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit - 1]
    comma = cut.rfind('、')
    return (cut[:comma] if comma >= limit // 2 else cut) + '…'


def lead_summary(description_html):
    """リード文から「この記事では〜」の文を選ぶ。無ければ最初の文。"""
    match = re.search(r'<p\b[^>]*>(.*?)</p>', description_html, re.S)
    lead = re.sub(r'<[^>]+>', '', match.group(1) if match else description_html)
    lead = re.sub(r'\s+', ' ', unescape(lead)).strip()
    sentences = [s for s in re.findall(r'[^。]+。?', lead) if s.strip()]
    if not sentences:
        return ''
    chosen = next((s for s in sentences if re.match(r'\s*(この記事|本記事|本稿)では', s)), sentences[0])
    return shorten(chosen)


def medical_news(rss_xml, config, public_videos):
    wanted = set(config['medical_categories'])
    out = []
    for item in ET.fromstring(rss_xml).findall('./channel/item'):
        url = (item.findtext('link') or '').strip()
        if not ENTRY_RE.fullmatch(url):
            continue
        categories = {clean_text(c.text or '') for c in item.findall('category')}
        if not categories & wanted:
            continue
        try:
            published = datetime.strptime(item.findtext('pubDate') or '', '%a, %d %b %Y %H:%M:%S %z').astimezone(JST)
        except ValueError:
            continue
        description = item.findtext('description') or ''
        title, label = split_title(item.findtext('title') or '')
        summary = lead_summary(description)
        if not title or not summary:
            continue
        video = next((v for v in EMBED_RE.findall(description) if v in public_videos), '')
        out.append({'title': title, 'url': url, 'date': published.date().isoformat(), 'audience_label': label,
                    'summary': summary, 'video': video, '_ts': published.isoformat()})
    out.sort(key=lambda r: r['_ts'], reverse=True)
    for row in out:
        row.pop('_ts')
    return out[:config['medical_news_count']]


def channel_video_ids(feed_xml):
    return re.findall(r'<yt:videoId>([\w-]{11})</yt:videoId>', feed_xml)


# ---- 実用ツールの近道 ----------------------------------------------------------

def tool_label(name):
    name = clean_text(name)
    name = re.sub(r'[（(][^）)]*[）)]\s*$', '', name).strip()
    return re.sub(r'\s*ツール$', '', name).strip()


def newest_first(urls, first_seen, today):
    """初めて見た日を記録し、新しい順（同じ日は一覧の並び順）に返す。"""
    for url in urls:
        first_seen.setdefault(url, today)
    order = {url: i for i, url in enumerate(urls)}
    return sorted(urls, key=lambda u: (first_seen[u], -order[u]), reverse=True)


def pro_tools(tool_html, config, state, today):
    parser = ToolParser()
    parser.feed(tool_html)
    tools = {item['u']: item['t'] for item in parser.items}
    if not tools:
        raise RuntimeError('ツール一覧が空です')
    staples = config['pro_tool_staples']
    staple_urls = {s['url'] for s in staples}
    ranked = [u for u in newest_first(list(tools), state.setdefault('tools_first_seen', {}), today) if u not in staple_urls]
    picked = [{'url': u, 'label': tool_label(tools[u])} for u in ranked[:config['new_tool_count']]]
    return picked + [s for s in staples if s['url'] in tools]


def general_tools(manifest, config, state, today):
    words = config['handout_audience_words']
    items = [i for i in manifest.get('items', []) if re.fullmatch(r'[a-z0-9-]+', i.get('slug', ''))
             and i.get('title') and any(w in i.get('audience', '') for w in words)]
    if not items:
        raise RuntimeError('一般向けの配布資料が見つかりません')
    titles = {f"{TOOLS}/handouts/{i['slug']}/": clean_text(i['title']) for i in items}
    ranked = newest_first(list(titles), state.setdefault('handouts_first_seen', {}), today)
    return [{'url': u, 'label': titles[u] + '（配布資料）'} for u in ranked[:config['new_handout_count']]]


# ---- オフライン版 -------------------------------------------------------------

def _counts_text(body, full):
    match = re.search(r'(\d+)件（ツール(\d+)・症状チェッカー(\d+)・ハンドアウト(?:HTML)?(\d+)(?:＋PDF\d+)?・図解(\d+)）', body)
    if not match:
        return ('ツール・症状チェッカー・ハンドアウト（HTMLと印刷用PDF）・図解' if full
                else 'ツール・症状チェッカー・ハンドアウト（HTML）。容量の制限が厳しい環境向け')
    total, tools, checker, handouts, figures = (int(x) for x in match.groups())
    if full:
        return f'{total}件：ツール{tools}・症状チェッカー{checker}・ハンドアウト{handouts}（HTMLと印刷用PDF）・図解{figures}'
    lite = re.search(r'軽量版\s*\**\s*(\d+)件', body) or re.search(r'(\d+)件（ツール\d+・症状チェッカー\d+・ハンドアウト(?:HTML)?\d+）', body)
    lite_total = int(lite.group(1)) if lite else tools + checker + handouts
    detail = f'：ツール{tools}・症状チェッカー{checker}・ハンドアウト{handouts}（HTML）' if lite_total == tools + checker + handouts else ''
    return f'{lite_total}件{detail}。容量の制限が厳しい環境向け'


def offline_release(releases_json):
    for rel in json.loads(releases_json):
        tag = rel.get('tag_name', '')
        if rel.get('draft') or rel.get('prerelease') or not re.fullmatch(r'offline-v\d+(?:\.\d+)*', tag):
            continue
        assets = {a.get('name', ''): a for a in rel.get('assets', [])}
        full = next((a for n, a in assets.items() if re.fullmatch(r'ichisouzo-offline-v[\w.-]*\.zip', n)), None)
        lite = next((a for n, a in assets.items() if re.fullmatch(r'ichisouzo-offline-lite-[\w.-]*\.zip', n)), None)
        if not full or not lite:
            continue
        stated = re.search(r'(20\d\d)-(\d{2})-(\d{2})', rel.get('name', '') + ' ' + (rel.get('body') or '')[:200])
        day = (date(*map(int, stated.groups())) if stated
               else datetime.fromisoformat(rel['published_at'].replace('Z', '+00:00')).astimezone(JST).date())
        body = rel.get('body') or ''
        edition = lambda a, is_full: {'url': a['browser_download_url'], 'size_mb': round(a['size'] / 1048576, 1),
                                      'text': _counts_text(body, is_full)}
        return {'version': tag[len('offline-'):], 'date': day.isoformat(), 'release_url': rel['html_url'],
                'full': edition(full, True), 'lite': edition(lite, False)}
    raise RuntimeError('offline-v* のリリースが見つかりません')


# ---- 最近更新した記事 ---------------------------------------------------------

NOTICE_DATE = r'(20\d\d)年(\d{1,2})月(\d{1,2})日'
NOTICE_PATTERNS = [
    # 2026年10月15日更新：〜 / 【2026年10月12日追記】〜（行頭の告知だけ。「〜日改訂の電子添文」は除く）
    re.compile(r'^[【\[［(（※■●◆・\s]*' + NOTICE_DATE + r'\s*(?:に)?(?:更新|改訂|追記|加筆)(?!の)(?:しました)?[】\]］)）]?\s*[：:]?\s*(.*)$'),
    # 最終確認・改訂日：2026年10月20日（〜）
    re.compile(r'^[【\[［(（※■●◆・\s]*(?:最終確認・)?(?:改訂日|更新日|最終改訂日|最終更新日)\s*[：:]\s*' + NOTICE_DATE + r'\s*(.*)$'),
]


def revision_notice(html, published, lastmod_day, window):
    """本文の改訂告知のうち、公開日より後で今回の lastmod に近い最新のものを返す。"""
    start = html.find('<div class="entry-content')
    end = html.find('<footer class="entry-footer', start)
    body = html[start:end] if start >= 0 and end > start else html
    lines = block_lines(body)
    best = None
    for i, line in enumerate(lines):
        for pattern in NOTICE_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            try:
                day = date(*(int(x) for x in match.groups()[:3]))
            except ValueError:
                continue
            if not (published + timedelta(days=2) <= day <= lastmod_day and (lastmod_day - day).days <= window):
                continue
            rest = re.sub(r'^[（(](.*)[）)]$', r'\1', match.group(4).strip())
            if not rest and i + 1 < len(lines):
                rest = lines[i + 1]
            summary = shorten(rest, 140) if rest else '記事の内容を更新しました。'
            if not best or day > best[0]:
                best = (day, summary, line)
    return best


def entry_title(html):
    match = re.search(r'class="entry-title-link[^"]*"[^>]*>(.*?)</a>', html, re.S)
    return clean_text(re.sub(r'<[^>]+>', '', match.group(1))) if match else ''


def sitemap_entries(index_xml, state, fetcher):
    """前回から lastmod が変わった月別サイトマップだけを読み、記事URLと lastmod を返す。"""
    seen = state.setdefault('sitemaps', {})
    entries, changed = {}, {}
    root = ET.fromstring(index_xml)
    for node in root:
        loc = next((c.text for c in node if c.tag.endswith('loc')), '')
        mod = next((c.text for c in node if c.tag.endswith('lastmod')), '')
        if not loc or not loc.startswith(BLOG + '/sitemap') or seen.get(loc) == mod:
            continue
        for url_node in ET.fromstring(fetcher(loc)):
            u = next((c.text for c in url_node if c.tag.endswith('loc')), '')
            m = next((c.text for c in url_node if c.tag.endswith('lastmod')), '')
            if u and m and ENTRY_RE.fullmatch(u):
                entries[u] = m
        changed[loc] = mod
    return entries, changed


def scan_revisions(index_xml, state, config, fetcher, today, sleep=1.5, log=print):
    """改訂告知の付いた記事を返す。取得は1回あたり revision_fetch_limit 件まで。"""
    rev = state.setdefault('revisions', {})
    watermark = rev.get('watermark', '')
    floor = (datetime.combine(today, datetime.min.time(), JST) - timedelta(days=config['revision_lookback_days'])).isoformat()
    entries, changed = sitemap_entries(index_xml, state, fetcher)
    pending = rev.setdefault('pending', {})
    for url, mod in entries.items():
        y, mo, d = (int(x) for x in ENTRY_RE.fullmatch(url).groups())
        mod_day = datetime.fromisoformat(mod).astimezone(JST).date()
        if mod > max(watermark, floor) and (mod_day - date(y, mo, d)).days >= 2:
            pending[url] = mod
    for url, mod in list(pending.items()):
        if mod <= floor:
            pending.pop(url)
    found = []
    for url, mod in sorted(pending.items(), key=lambda kv: kv[1], reverse=True)[:config['revision_fetch_limit']]:
        y, mo, d = (int(x) for x in ENTRY_RE.fullmatch(url).groups())
        try:
            html = fetcher(url)
        except Exception as exc:  # 1記事の失敗で全体を止めない。次回に再試行する。
            log(f'  skip {url}: {exc}')
            continue
        finally:
            if sleep:
                time.sleep(sleep)
        pending.pop(url)
        notice = revision_notice(html, date(y, mo, d), datetime.fromisoformat(mod).astimezone(JST).date(),
                                 config['revision_notice_window_days'])
        title = entry_title(html)
        if notice and title:
            day, summary, line = notice
            found.append({'id': f'auto-{y}{mo:02d}{d:02d}-{url[-6:]}-{day:%Y%m%d}', 'date': day.isoformat(),
                          'title': title, 'summary': summary, 'url': url, 'public_verified': True, 'source': 'auto',
                          'evidence': f'自動登録：公開URLの本文にある改訂告知「{shorten(line, 80)}」'
                                      f'（取得 {datetime.now(JST):%Y-%m-%d %H:%M} JST・サイトマップ lastmod {mod}）'})
    if entries:
        newest = max(entries.values())
        if newest > watermark:
            rev['watermark'] = newest
    state['sitemaps'].update(changed)
    return found


def merge_updates(rows, found):
    """同じ記事のより新しい改訂だけを足す。手で登録した行は変更しない。"""
    latest = {}
    for row in rows:
        latest[row['url']] = max(latest.get(row['url'], ''), row['date'])
    added = []
    for row in found:
        if row['date'] > latest.get(row['url'], '') and all(r['id'] != row['id'] for r in rows):
            rows.append(row)
            latest[row['url']] = row['date']
            added.append(row)
    return added


# ---- 実行 --------------------------------------------------------------------

def load_json(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-revisions', action='store_true',
                        help='初回導入用。今のサイトマップを既読にし、本文は取得しない')
    parser.add_argument('--dry-run', action='store_true', help='書き込まずに結果を表示する')
    args = parser.parse_args()
    config = load_json(CONFIG_PATH, None)
    feed = load_json(FEED_PATH, {})
    state = load_json(STATE_PATH, {})
    today = today_jst().isoformat()
    failures = []

    def section(name, fn):
        try:
            fn()
            print(f'ok   {name}')
        except Exception as exc:  # 枠ごとに前回のデータを残す
            failures.append(name)
            print(f'WARN {name}: 前回のデータを維持します（{type(exc).__name__}: {exc}）')

    def videos():
        ids = channel_video_ids(fetch(CHANNEL_FEED))
        if not ids:
            raise RuntimeError('公開フィードに動画がありません')
        known = state.get('public_videos', [])
        state['public_videos'] = (ids + [v for v in known if v not in ids])[:400]

    def news():
        feed['medical_news'] = medical_news(fetch(BLOG + '/rss'), config, set(state.get('public_videos', [])))
        if not feed['medical_news']:
            raise RuntimeError('医学カテゴリーの記事がRSSにありません')

    def tools():
        feed['pro_tools'] = pro_tools(fetch(TOOLS + '/'), config, state, today)
        feed['general_tools'] = general_tools(json.loads(fetch(TOOLS + '/handouts/manifest.json')), config, state, today)

    def offline():
        feed['offline'] = offline_release(fetch(RELEASES_API, 'application/vnd.github+json'))

    updates = load_json(UPDATES_PATH, [])
    added = []

    def revisions():
        index_xml = fetch(BLOG + '/sitemap.xml')
        if args.seed_revisions:
            entries, changed = sitemap_entries(index_xml, state, fetch)
            state['sitemaps'].update(changed)
            state['revisions'] = {'watermark': max(entries.values()), 'pending': {}}
            print(f'  seeded watermark {state["revisions"]["watermark"]} ({len(entries)} entries)')
            return
        found = scan_revisions(index_xml, state, config, fetch, today_jst())
        candidate = list(updates)
        new = merge_updates(candidate, found)
        validate_updates(candidate)  # 不正な行があれば台帳を書き換えない
        updates[:] = candidate
        added.extend(new)
        print(f'  pending {len(state["revisions"]["pending"])}, added {len(added)}')

    section('動画の公開確認', videos)
    section('医学の新着', news)
    section('実用ツールの近道', tools)
    section('オフライン版', offline)
    section('最近更新した記事', revisions)
    for row in added:
        print(f'  + {row["date"]} {row["title"]} — {row["summary"]}')
    # 書き込む前に、トップへ埋め込めるかを確かめる（不正な値で index.html を壊さない）。
    probe = '\n'.join(('<!-- MEDICAL_NEWS -->', '<!-- PRO_TOOL_SHORTCUTS -->', '<!-- GENERAL_TOOL_SHORTCUTS -->',
                       '<!-- OFFLINE_ASIDE -->', '<!-- OFFLINE_CARDS -->', '<!-- OFFLINE_RELEASE_LINK -->'))
    apply_sections(probe, feed)
    if args.dry_run:
        print(json.dumps(feed, ensure_ascii=False, indent=2))
        return
    previous = load_json(FEED_PATH, {})
    previous.pop('updated', None)
    if {k: v for k, v in feed.items() if k != 'updated'} != previous:  # 中身が同じなら時刻だけのコミットを作らない
        feed['updated'] = datetime.now(timezone.utc).isoformat()
        write_json(FEED_PATH, feed)
    write_json(STATE_PATH, state)
    if added:
        write_json(UPDATES_PATH, updates)
    if failures:
        print('取得できなかった枠: ' + '・'.join(failures))


if __name__ == '__main__':
    main()
