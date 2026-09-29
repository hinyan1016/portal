"""公開サイトのカタログを更新。ローカル原稿を公開データへ混入させない。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BLOG = 'https://blog.ichisouzo-lab.com'
TOOLS = 'https://tools.ichisouzo-lab.com'

def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'IchisouzoCatalog/2.0'}), timeout=30) as response:
        return response.read().decode('utf-8')

def audience(title, tags):
    text = ' '.join(tags)
    pro = bool(re.search('医療従事者|医療者|医師向け|初期研修医|医向け', text))
    general = '一般向け' in text or '一般の方' in text
    if re.search('医療従事者向け|医師向け|医向け', title):
        return 'professional'
    return 'both' if pro and general else 'professional' if pro else 'general' if general else 'unspecified'

def rss_records(xml):
    out = []
    for item in ET.fromstring(xml).findall('./channel/item'):
        title, url = item.findtext('title', ''), item.findtext('link', '')
        if not url.startswith(BLOG + '/entry/'):
            continue
        cats = [x.text or '' for x in item.findall('category')]
        try:
            date = parsedate_to_datetime(item.findtext('pubDate')).date().isoformat()
        except (ValueError, TypeError, AttributeError):
            date = ''
        out.append({'t': title, 'u': url, 'k': '記事', 'a': audience(title, cats), 'd': date, 'tags': cats})
    return out

class ToolParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items, self.current, self.capture = [], None, False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'tool-card' in attrs.get('class', '').split():
            url = urljoin(TOOLS + '/', attrs.get('href', ''))
            self.current = {'t': '', 'u': url, 'k': 'ツール', 'a': 'professional', 'tags': []} if urlparse(url).netloc == urlparse(TOOLS).netloc and url.endswith('.html') else None
        if self.current and tag == 'div' and 'tool-name' in attrs.get('class', '').split():
            self.capture = True
    def handle_data(self, data):
        if self.current is not None and self.capture:
            self.current['t'] += data
    def handle_endtag(self, tag):
        if tag == 'div':
            self.capture = False
        if tag == 'a' and self.current:
            if self.current['t'].strip():
                self.current['t'] = self.current['t'].strip()
                self.items.append(self.current)
            self.current = None

def manifest_records(data, kind):
    out = []
    for item in data.get('items' if kind == '図解' else 'decks', []):
        slug = item.get('slug', '')
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', slug) or not item.get('title'):
            continue
        tags = item.get('tags', []) + [item.get('audience', ''), item.get('subtitle', '')]
        url = TOOLS + ('/infographics/' if kind == '図解' else '/slides/') + slug + '/'
        record = {'t': item['title'], 'u': url, 'k': kind, 'a': audience(item['title'], tags), 'd': item.get('date') or item.get('published_date', ''), 'tags': tags}
        record['group'] = item.get('blog_url', '')
        if kind == '図解':
            record['img'] = url + 'thumb.png'
        if item.get('slide_count'):
            record['pages'] = item['slide_count']
        out.append(record)
        video = item.get('youtube_id', '')
        if re.fullmatch(r'[\w-]{11}', video):
            out.append({'t': item['title'], 'u': 'https://www.youtube.com/watch?v=' + video, 'k': '動画', 'a': record['a'], 'd': record['d'], 'tags': tags, 'img': 'https://i.ytimg.com/vi/' + video + '/hqdefault.jpg', 'group': record['group']})
    return out

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, help='公開サイトマップにあるURLのメタデータだけを補完')
    args = parser.parse_args()
    urls = [BLOG + '/rss', TOOLS + '/infographics/manifest.json', TOOLS + '/slides/manifest.json', TOOLS + '/', BLOG + '/sitemap.xml']
    with ThreadPoolExecutor(max_workers=5) as pool:
        rss, ig, slides, tool_html, sitemap = list(pool.map(fetch, urls))
        submaps = [x.text for x in ET.fromstring(sitemap).iter() if x.tag.endswith('loc') and x.text and x.text.startswith(BLOG + '/sitemap')]
        maps = list(pool.map(fetch, submaps))
    if not maps:
        raise RuntimeError('公開サイトマップを取得できません。既存カタログを保持します。')
    published = {x.text for xml in maps for x in ET.fromstring(xml).iter() if x.tag.endswith('loc') and x.text and x.text.startswith(BLOG + '/entry/')}
    if not published:
        raise RuntimeError('公開記事が0件。既存カタログを保持します。')
    old = json.loads((ROOT / 'search-index.json').read_text(encoding='utf-8'))
    records = {x['u']: x for x in old if x.get('k') == '記事' and x.get('u') in published}
    if args.corpus:
        for r in json.loads(args.corpus.read_text(encoding='utf-8')):
            if r.get('draft') != 'yes' and r.get('url') in published:
                tags = r.get('categories') or []
                records[r['url']] = {'t': r['title'], 'u': r['url'], 'k': '記事', 'a': audience(r['title'], tags), 'd': r.get('published', '')[:10], 'tags': tags}
    fresh = rss_records(rss)
    parser = ToolParser()
    parser.feed(tool_html)
    if not fresh or not parser.items:
        raise RuntimeError('RSSまたはツール一覧が空です。既存カタログを保持します。')
    ig_data = json.loads(ig)
    fresh += parser.items + manifest_records(ig_data, '図解') + manifest_records(json.loads(slides), 'スライド')
    for record in fresh:
        previous = records.get(record['u'], {})
        if record['k'] == '動画' and previous.get('a') not in (None, 'unspecified') and record['a'] == 'unspecified':
            record['a'] = previous['a']
        records[record['u']] = record
    for entry in ig_data.get('items', []):
        if entry.get('blog_url') in records and re.fullmatch(r'[a-zA-Z0-9_-]+', entry.get('slug', '')):
            records[entry['blog_url']]['img'] = TOOLS + '/infographics/' + entry['slug'] + '/thumb.png'
    for record in records.values():
        record.setdefault('a', 'unspecified')
        record.setdefault('tags', [])
        record.setdefault('d', '')
    ordered = sorted(records.values(), key=lambda r: r.get('d', ''), reverse=True)
    # 全取得・解析が完了してから書込。通信失敗で正常データを空にしない。
    (ROOT / 'search-index.json').write_text(json.dumps(ordered, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    (ROOT / 'catalog-meta.json').write_text(json.dumps({'updated': datetime.now(timezone.utc).isoformat(), 'items': len(ordered), 'sources': urls[:4]}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Updated {len(ordered)} public records; {len(published)} sitemap URLs checked')

if __name__ == '__main__':
    main()
