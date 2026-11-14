"""ブログトップの記事カードに使う16:9サムネイルの対応表（blog-thumbs.json）を作る。

公開カタログ search-index.json（約0.8MB）をブログ側で読むと重いので、
記事の日時（entry/ 以下）と軽量サムネイルのパスだけを抜き出す。
stage_site.py が公開のたびに作り直すため、記事やサムネイルが増えても手作業は要らない。
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ENTRY = re.compile(r'https://blog\.ichisouzo-lab\.com/entry/(\d{4}/\d{2}/\d{2}/\d{6})')
THUMB = re.compile(r'thumbs/[A-Za-z0-9/_.-]+\.webp')


def build_map(items, thumbs_dir=None):
    """カタログの記事から {"YYYY/MM/DD/HHMMSS": "thumbs/....webp"} を作る。

    想定外の形のURL・画像パスは載せない。thumbs_dir を渡したときは、実在する画像だけを載せる。
    同じ記事が複数あれば先に出たものを使う（カタログの並びが総合ホームの表示と同じため）。
    """
    out = {}
    for item in items:
        m = ENTRY.fullmatch(item.get('u') or '')
        img = item.get('img') or ''
        if not m or not THUMB.fullmatch(img) or '..' in img:
            continue
        if thumbs_dir is not None and not (thumbs_dir.parent / img).is_file():
            continue
        out.setdefault(m.group(1), img)
    return out


def write(out_path, root=ROOT):
    items = json.loads((root / 'search-index.json').read_text(encoding='utf-8'))
    data = {'v': 1, 'base': 'https://ichisouzo-lab.com/', 'map': build_map(items, root / 'thumbs')}
    Path(out_path).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return len(data['map'])


if __name__ == '__main__':
    print(write(ROOT / 'blog-thumbs.json'), 'entries')
