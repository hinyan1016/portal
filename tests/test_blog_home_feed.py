"""ブログトップ第5段用軽量フィード（blog-home-feed.json）の生成を検証する。"""
import json
from pathlib import Path

from scripts import blog_home_feed

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PROFILE = ('大津赤十字', '部長', 'いまむら ひさし', 'hinyan1016')


def test_build_feed_validates_urls_and_excludes_non_medical(tmp_path):
    (tmp_path / 'thumbs').mkdir()
    (tmp_path / 'thumbs' / 'ok.webp').write_bytes(b'x')

    items = [
        {
            'k': '記事',
            'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/13/193200',
            't': '脳卒中の最新解説',
            'd': '2026-11-13',
            'a': 'professional',
            'tags': ['医学情報', '脳神経内科', '脳卒中'],
            'img': 'thumbs/ok.webp',
        },
        {
            'k': '記事',
            'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/12/120000',
            't': '【米子観光ガイド】温泉とグルメ',
            'd': '2026-11-12',
            'a': 'unspecified',
            'tags': ['旅・地域', '医学情報'],
            'img': 'thumbs/ok.webp',
        },
        {
            'k': '記事',
            'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/11/120000',
            't': 'AIベンチマーク解説',
            'd': '2026-11-11',
            'a': 'unspecified',
            'tags': ['AI活用'],
            'img': 'thumbs/ok.webp',
        },
        {
            'k': '記事',
            'u': 'https://blog.ichisouzo-lab.com/entry/2026/11/10/120000',
            't': '頭痛が続くときの受診目安',
            'd': '2026-11-10',
            'a': 'general',
            'tags': ['頭痛'],
            'img': 'thumbs/../evil.webp',
        },
        {
            'k': '動画',
            'u': 'https://www.youtube.com/watch?v=C_j1kZqfUsc',
            'group': 'https://blog.ichisouzo-lab.com/entry/2026/11/13/193200',
        },
        {
            'k': '動画',
            'u': 'https://evil.example/watch?v=bad',
            'group': 'https://blog.ichisouzo-lab.com/entry/2026/11/10/120000',
        },
        {
            'k': 'スライド',
            'u': 'https://tools.ichisouzo-lab.com/slides/carotid-web-a-to-a-stroke/',
            'group': 'https://blog.ichisouzo-lab.com/entry/2026/11/13/193200',
            'pages': 15,
        },
        {
            'k': 'スライド',
            'u': 'https://tools.ichisouzo-lab.com/slides/../bad/',
            'group': 'https://blog.ichisouzo-lab.com/entry/2026/11/10/120000',
            'pages': 10,
        },
    ]

    data = blog_home_feed.build_feed(items, stats={'articles': 10, 'slides': 5, 'tools': 3, 'infographics': 2}, thumbs_dir=tmp_path / 'thumbs')
    assert [e['id'] for e in data['feeds']['all']] == ['2026/11/13/193200', '2026/11/10/120000']
    assert data['feeds']['doctor'][0]['cats'][0] == '医師向け'
    assert '医学情報' not in data['feeds']['doctor'][0]['cats']
    assert data['feeds']['general'][0]['cats'][0] == '一般向け'
    assert data['feeds']['general'][0]['img'] == ''
    assert data['media'] == {
        '2026/11/13/193200': {'v': 'C_j1kZqfUsc', 's': 'carotid-web-a-to-a-stroke', 'p': 15}
    }
    assert len(data['showcase']) == 1 and data['showcase'][0]['aud'] == '医師向け'
    assert data['stats']['videos'] == 2


def test_write_real_feed_meets_size_counts_and_privacy(tmp_path):
    out = tmp_path / 'blog-home-feed.json'
    media_count = blog_home_feed.write(out)
    raw = out.read_text(encoding='utf-8')
    assert media_count > 100
    assert out.stat().st_size < 60_000
    for forbidden in FORBIDDEN_PROFILE:
        assert forbidden not in raw

    data = json.loads(raw)
    assert data['v'] == 1 and data['base'] == 'https://ichisouzo-lab.com/'
    for tab in ('all', 'doctor', 'general', 'media'):
        assert len(data['feeds'][tab]) >= 8
    assert len(data['showcase']) == 4
    assert data['stats']['articles'] >= 1300
    assert data['stats']['videos'] >= 200
    assert data['stats']['slides'] >= 200
    assert data['stats']['tools'] >= 70


def test_stage5_assets_are_staged_and_clean():
    from scripts import stage_site

    for name in ('blog-home-stage5.css', 'blog-home-stage5.js'):
        assert name in stage_site.FILES
        p = ROOT / name
        assert p.is_file()
        txt = p.read_text(encoding='utf-8')
        assert len(txt) > 1000
        for forbidden in FORBIDDEN_PROFILE:
            assert forbidden not in txt
    assert 'setupInlineTabs' in (ROOT / 'blog-home-stage5.js').read_text(encoding='utf-8')
    assert 'ichisouzo-home-v3-stage5-20261115' in (ROOT / 'blog-home-stage5.css').read_text(encoding='utf-8')

