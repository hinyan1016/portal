"""図解カード用の軽量サムネイル（WebP）を作る。

公開中の図解は縦長PNG（1枚およそ1.5〜2MB）で、トップのカードに原寸を読むと初回表示が十数MBになる。
カードと同じ16:9で上部を切り出し、幅800px以下のWebPにして thumbs/<slug>.webp に置く。
元画像の大きさ（Content-Length）を thumbs/sources.json に記録し、変わった図解だけを作り直す。
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TOOLS = 'https://tools.ichisouzo-lab.com'
OUT = ROOT / 'thumbs'
WIDTH, HEIGHT = 800, 450
SLUG = re.compile(r'[A-Za-z0-9_-]+')
HEADERS = {'User-Agent': 'IchisouzoThumbs/1.0'}


def remote_size(url):
    """公開画像の大きさ。無ければ None。"""
    try:
        with urlopen(Request(url, headers=HEADERS, method='HEAD'), timeout=30) as response:
            size = response.headers.get('Content-Length', '')
            return int(size) if size.isdigit() else -1
    except HTTPError as error:
        if error.code == 404:
            return None
        raise


def download(url):
    with urlopen(Request(url, headers=HEADERS), timeout=60) as response:
        return response.read()


def source_bytes(url, local, size):
    """公開版と同じ大きさのローカル複製があればそれを使い、なければ公開版を取得する。"""
    if local and local.is_file() and local.stat().st_size == size:
        return local.read_bytes()
    return download(url)


def is_strip(data):
    """タイトル帯だけの極端に横長な thumb.png はカードに使わない。"""
    with Image.open(io.BytesIO(data)) as image:
        return image.width > image.height * 3


def flatten(image):
    """透明部分は白で塗り、RGBにそろえる。"""
    if image.mode == 'P':
        image = image.convert('RGBA')
    if image.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', image.size, 'white')
        background.paste(image, mask=image.getchannel('A'))
        return background
    return image.convert('RGB')


def card_image(data):
    """カードと同じく上寄せで16:9に切り出し、幅800px以下のWebPにする。拡大はしない。"""
    with Image.open(io.BytesIO(data)) as source:
        image = flatten(source)
    width, height = image.size
    if width * HEIGHT > height * WIDTH:
        crop = round(height * WIDTH / HEIGHT)
        left = (width - crop) // 2
        image = image.crop((left, 0, left + crop, height))
    else:
        image = image.crop((0, 0, width, round(width * HEIGHT / WIDTH)))
    if image.width > WIDTH:
        image = image.resize((WIDTH, HEIGHT), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, 'WEBP', quality=80, method=6)
    return buffer.getvalue()


def build(slug, known, tools_dir):
    """(slug, 記録, 状態) を返す。状態は kept / made / missing。"""
    target = OUT / f'{slug}.webp'
    if known and target.exists() and remote_size(f'{TOOLS}/infographics/{slug}/{known["source"]}') == known['bytes']:
        return slug, known, 'kept'
    for name in ('thumb.png', 'infographic.png'):
        url = f'{TOOLS}/infographics/{slug}/{name}'
        size = remote_size(url)
        if size is None:
            continue
        local = tools_dir / 'infographics' / slug / name if tools_dir else None
        data = source_bytes(url, local, size)
        if name == 'thumb.png' and is_strip(data):
            continue
        target.write_bytes(card_image(data))
        return slug, {'source': name, 'bytes': size if size >= 0 else len(data)}, 'made'
    return slug, None, 'missing'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools-dir', type=Path, help='medical-ddx-tools のローカル複製。公開版と同じ大きさの画像だけを流用する')
    parser.add_argument('--workers', type=int, choices=range(1, 9), default=6)
    args = parser.parse_args()
    manifest = json.loads(download(TOOLS + '/infographics/manifest.json'))
    slugs = sorted({item.get('slug', '') for item in manifest.get('items', []) if SLUG.fullmatch(item.get('slug', ''))})
    if not slugs:
        raise RuntimeError('図解マニフェストが空です。既存のサムネイルを保持します。')
    OUT.mkdir(exist_ok=True)
    record_path = OUT / 'sources.json'
    records = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else {}
    status, failed = {'kept': 0, 'made': 0, 'missing': 0}, []

    def task(slug):
        try:
            return build(slug, records.get(slug), args.tools_dir)
        except (URLError, OSError, ValueError) as error:
            # 通信や画像の不具合は、その図解だけ見送る。既存のサムネイルは消さない。
            failed.append(f'{slug}: {error}')
            return slug, records.get(slug), 'failed'

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for slug, record, state in pool.map(task, slugs):
            if record:
                records[slug] = record
            if state in status:
                status[state] += 1
    # 公開一覧から外れた図解のサムネイルは配信しない。
    for path in OUT.glob('*.webp'):
        if path.stem not in slugs:
            path.unlink()
    records = {slug: records[slug] for slug in slugs if slug in records and (OUT / f'{slug}.webp').exists()}
    record_path.write_text(json.dumps(records, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    total = sum(path.stat().st_size for path in OUT.glob('*.webp'))
    print(f'Thumbnails: {status}, failed={len(failed)}, files={len(records)}, total={total // 1024}KB')
    for line in failed:
        print('  failed', line)


if __name__ == '__main__':
    main()
