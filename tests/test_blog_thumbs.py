"""ブログトップ用サムネイル対応表（blog-thumbs.json）の生成を検証する。"""
import json
from pathlib import Path

from scripts import blog_thumbs

ROOT = Path(__file__).resolve().parents[1]


def test_build_map_keeps_only_valid_blog_entries():
    items = [
        {'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/13/193200', 'img': 'thumbs/carotid.webp'},
        {'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/13/193200', 'img': 'thumbs/articles/x.webp'},
        {'u': 'https://blog.ichisouzo-lab.com/entry/2026/08/28/131357_1', 'img': 'thumbs/a.webp'},
        {'u': 'https://tools.ichisouzo-lab.com/a.html', 'img': 'thumbs/b.webp'},
        {'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/12/000000', 'img': 'https://evil.example/x.webp'},
        {'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/11/000000', 'img': 'thumbs/../x.webp'},
        {'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/10/000000'},
    ]
    assert blog_thumbs.build_map(items) == {'2026/11/13/193200': 'thumbs/carotid.webp'}


def test_build_map_drops_missing_files(tmp_path):
    (tmp_path / 'thumbs').mkdir()
    (tmp_path / 'thumbs' / 'ok.webp').write_bytes(b'x')
    items = [
        {'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/13/000001', 'img': 'thumbs/ok.webp'},
        {'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/13/000002', 'img': 'thumbs/missing.webp'},
    ]
    assert blog_thumbs.build_map(items, tmp_path / 'thumbs') == {'2026/11/13/000001': 'thumbs/ok.webp'}


def test_write_real_catalog_is_small_and_covers_latest_articles(tmp_path):
    out = tmp_path / 'blog-thumbs.json'
    count = blog_thumbs.write(out)
    data = json.loads(out.read_text(encoding='utf-8'))
    assert data['v'] == 1 and data['base'] == 'https://ichisouzo-lab.com/'
    assert count == len(data['map']) > 1000
    assert out.stat().st_size < 150_000
    items = json.loads((ROOT / 'search-index.json').read_text(encoding='utf-8'))
    latest = [i for i in items if i['u'].startswith('https://blog.ichisouzo-lab.com/entry/') and i.get('img')][:8]
    for item in latest:
        key = item['u'].split('/entry/')[1]
        assert data['map'].get(key) == item['img']
