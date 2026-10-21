"""記事カード用画像（アイキャッチ由来）の対応づけを検証する。"""
import json

from scripts import article_images as ai
from scripts.refresh_catalog import apply_article_images

SIG = 'https://cdn.image.st-hatena.com/image/scale/91e5/backend=imagemagick;height=500;quality=80;version=1;width=500/'


def section(url, thumb=''):
    style = f'<div class="entry-thumb" style="background-image: url(\'{thumb}\');"></div>' if thumb else ''
    return (f'<section class="archive-entry test-archive-entry"><h1 class="entry-title">'
            f'<a class="entry-title-link" href="{url}">題名</a></h1><a class="entry-thumb-link">{style}</a></section>')


def test_archive_entries_reads_links_thumbs_and_pager():
    html = (section('https://blog.ichisouzo-lab.com/entry/2026/10/21/084039', SIG + 'https%3A%2F%2Fcdn-ak.f.st-hatena.com%2Fimages%2Ffotolife%2Fh%2Fx%2F1.png')
            + section('https://blog.ichisouzo-lab.com/entry/2026/10/20/000000')
            + section('https://evil.example/entry/2026/10/20/000000', SIG + 'x')
            + '<a href="?page=2" rel="next">次</a>')
    rows, more = ai.archive_entries(html)
    assert more and len(rows) == 2 and rows[1] == ('https://blog.ichisouzo-lab.com/entry/2026/10/20/000000', '')


def test_source_url_prefers_allowed_original():
    fotolife = 'https://cdn-ak.f.st-hatena.com/images/fotolife/h/x/1.png'
    assert ai.source_url(SIG + 'https%3A%2F%2Fcdn-ak.f.st-hatena.com%2Fimages%2Ffotolife%2Fh%2Fx%2F1.png') == fotolife
    # 許可していないホストの元画像は取得せず、はてなの縮小版を使う
    assert ai.source_url(SIG + 'https%3A%2F%2Fevil.example%2Fa.png') == SIG + 'https%3A%2F%2Fevil.example%2Fa.png'
    assert ai.source_url('https://evil.example/a.png') == ''
    assert ai.infographic_slug('https://tools.ichisouzo-lab.com/infographics/lgs-dx/infographic.png') == 'lgs-dx'
    assert ai.infographic_slug('https://tools.ichisouzo-lab.com/infographics/../x/a.png') == ''


def test_plan_reuses_infographic_thumbs_and_skips_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(ai, 'ROOT', tmp_path)
    (tmp_path / 'thumbs' / 'articles').mkdir(parents=True)
    (tmp_path / 'thumbs' / 'lgs.webp').write_bytes(b'x')
    (tmp_path / 'thumbs' / 'articles' / '20261019-000000.webp').write_bytes(b'x')
    a, b, c, d = (f'https://blog.ichisouzo-lab.com/entry/2026/10/{n}/000000' for n in (18, 19, 20, 21))
    src_b = 'https://cdn-ak.f.st-hatena.com/images/fotolife/h/x/b.png'
    mapping = {b: {'src': src_b, 'img': 'thumbs/articles/20261019-000000.webp'}}
    entries = [(a, SIG + 'https%3A%2F%2Ftools.ichisouzo-lab.com%2Finfographics%2Flgs%2Finfographic.png'),
               (b, SIG + 'https%3A%2F%2Fcdn-ak.f.st-hatena.com%2Fimages%2Ffotolife%2Fh%2Fx%2Fb.png'),
               (c, SIG + 'https%3A%2F%2Fcdn-ak.f.st-hatena.com%2Fimages%2Ffotolife%2Fh%2Fx%2Fc.png'), (d, '')]
    todo = ai.plan(entries, mapping)
    assert mapping[a]['img'] == 'thumbs/lgs.webp' and mapping[d] == {'src': '', 'img': ''}
    assert todo == [(c, 'https://cdn-ak.f.st-hatena.com/images/fotolife/h/x/c.png', 'thumbs/articles/20261020-000000.webp')]


def test_catalog_uses_eyecatch_only_when_manifest_has_none(tmp_path, monkeypatch):
    import scripts.refresh_catalog as rc
    monkeypatch.setattr(rc, 'ROOT', tmp_path)
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'thumbs' / 'articles').mkdir(parents=True)
    (tmp_path / 'thumbs' / 'articles' / 'a.webp').write_bytes(b'x')
    u1, u2, u3 = (f'https://blog.ichisouzo-lab.com/entry/2026/10/2{n}/000000' for n in (1, 2, 3))
    (tmp_path / 'scripts' / 'article_images.json').write_text(json.dumps({'articles': {
        u1: {'img': 'thumbs/articles/a.webp'}, u2: {'img': 'thumbs/articles/a.webp'}, u3: {'img': 'thumbs/articles/gone.webp'}}}), encoding='utf-8')
    records = {u1: {'k': '記事'}, u2: {'k': '記事', 'img': 'thumbs/manifest.webp'},
               u3: {'k': '記事', 'img': 'thumbs/articles/gone.webp'}}
    assert apply_article_images(records, skip={u2}) == 1
    assert records[u1]['img'] == 'thumbs/articles/a.webp'
    assert records[u2]['img'] == 'thumbs/manifest.webp'  # 図解マニフェストの画像を優先
    assert 'img' not in records[u3]  # 消えたサムネイルを参照しない
