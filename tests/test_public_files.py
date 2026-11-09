"""検索エンジン向けの案内（robots.txt・sitemap.xml）とアイコンが配信対象に入っていることを検証する。"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.stage_site import FILES

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://ichisouzo-lab.com/'
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


def sitemap_urls():
    tree = ET.parse(ROOT / 'sitemap.xml')
    return [loc.text for loc in tree.getroot().findall('s:url/s:loc', NS)]


def test_crawler_files_are_staged_and_exist():
    for name in ('robots.txt', 'sitemap.xml', 'favicon.ico'):
        assert name in FILES
        assert (ROOT / name).is_file()
    assert len(FILES) == len(set(FILES))


def test_robots_allows_crawling_and_points_to_sitemap():
    lines = (ROOT / 'robots.txt').read_text(encoding='utf-8').splitlines()
    assert 'User-agent: *' in lines and 'Allow: /' in lines
    assert not [line for line in lines if line.startswith('Disallow')]
    assert 'Sitemap: ' + SITE + 'sitemap.xml' in lines


def test_sitemap_lists_only_indexable_pages_with_their_canonical_url():
    urls = sitemap_urls()
    assert urls[0] == SITE and len(urls) == len(set(urls))
    for url in urls:
        assert url.startswith(SITE)
        name = url[len(SITE):] or 'index.html'
        assert name in FILES
        html = (ROOT / name).read_text(encoding='utf-8')
        assert 'noindex' not in html
        assert '<link rel="canonical" href="' + url + '">' in html


def test_every_indexable_page_is_in_sitemap():
    urls = sitemap_urls()
    for name in FILES:
        if not name.endswith('.html'):
            continue
        html = (ROOT / name).read_text(encoding='utf-8')
        if re.search(r'<meta name="robots"[^>]*noindex', html):
            continue
        assert SITE + ('' if name == 'index.html' else name) in urls
