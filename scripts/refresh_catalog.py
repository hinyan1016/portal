"""公開サイトのカタログを更新。ローカル原稿を公開データへ混入させない。"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BLOG = 'https://blog.ichisouzo-lab.com'
TOOLS = 'https://tools.ichisouzo-lab.com'
AUDIENCES = {'professional', 'general', 'both', 'unspecified'}
SERIES_IDS = {'body-mysteries', 'anti-aging'}


def validated_series(value):
    """本文の証拠・私的フィールドを公開インデックスへ出さず、許可した識別子と番号だけ返す。"""
    if (isinstance(value, dict) and value.get('id') in SERIES_IDS
            and type(value.get('number')) is int and 1 <= value['number'] <= 999):
        return {'id': value['id'], 'number': value['number']}
    return None


def apply_series_metadata(records, metadata, published):
    """実測済みの対応を、今回も公開確認できた記事のみに適用する。"""
    applied = 0
    for url, value in metadata.items():
        record, series = records.get(url), validated_series(value)
        if url in published and record and record.get('k') == '記事' and series:
            record['series'] = series
            applied += 1
    return applied


def clean_text(value):
    """二重エスケープされた公開見出しも、検索できる通常の文字へ戻す。"""
    value = str(value or '')
    for _ in range(3):
        decoded = unescape(value)
        if decoded == value:
            break
        value = decoded
    return value.strip()


def clean_tags(tags):
    return list(dict.fromkeys(clean_text(tag) for tag in tags if clean_text(tag)))

def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'IchisouzoCatalog/2.0'}), timeout=30) as response:
        return response.read().decode('utf-8')


def card_image(slug):
    """scripts/build_thumbs.py で作った軽量サムネイルの相対パス。未作成なら空文字。"""
    return f'thumbs/{slug}.webp' if (ROOT / 'thumbs' / f'{slug}.webp').is_file() else ''


def set_card_image(record, slug):
    image = card_image(slug)
    if image:
        record['img'] = image
    else:
        record.pop('img', None)


def replace_legacy_image(record):
    """原寸PNGへ切り替わる旧形式の図解画像URLを、軽量サムネイルに置き換える。"""
    legacy = re.fullmatch(re.escape(TOOLS) + r'/infographics/([a-zA-Z0-9_-]+)/thumb\.png', record.get('img', ''))
    if legacy:
        set_card_image(record, legacy.group(1))

def audience(title, tags, declared=''):
    """明記された対象読者だけを分類。医学テーマや文体から推測しない。"""
    fields = [unicodedata.normalize('NFKC', clean_text(tag)) for tag in tags]
    declared = unicodedata.normalize('NFKC', clean_text(declared))
    fields.append(declared)
    text = ' '.join(fields)
    pro = bool(re.search('医療従事者|医療者|医師向け|初期研修医|研修医向け|医向け', text))
    general = bool(re.search('一般向け|一般の方|患者向け', text))
    # 「一般」「患者」は audience フィールドまたは独立した分類値の場合のみ。
    # 「一般医療機器」「外来患者指導」などの話題タグと混同しない。
    general = general or any(tag in {'一般', '患者・一般', '一般・患者'} for tag in fields)
    general = general or any(re.search(r'(?:^|[・/、,])(?:一般|患者)(?:$|[・/、,])', tag) for tag in fields)
    title = unicodedata.normalize('NFKC', clean_text(title))
    title_pro = bool(re.search('医療従事者向け|医療者向け|医師向け|研修医向け|非専門医向け|医向け', title))
    title_general = bool(re.search('一般向け|一般の方向け|患者(?:さん)?向け|(?:ご)?家族向け', title))
    # 共通の「向け」を末尾に置く、明示的な複数読者の表記も拾う。
    title_pro = title_pro or bool(re.search(r'(?:医療従事者|医療者|医師|研修医|非専門医)[・&/、と]+(?:一般(?:の方)?|患者(?:さん)?|ご?家族)向け', title))
    title_general = title_general or bool(re.search(r'(?:一般(?:の方)?|患者(?:さん)?|ご?家族)[・&/、と]+(?:医療従事者|医療者|医師|研修医|非専門医)向け', title))
    if title_pro or title_general:
        return 'both' if title_pro and title_general else 'professional' if title_pro else 'general'
    return 'both' if pro and general else 'professional' if pro else 'general' if general else 'unspecified'


def merge_record(previous, fresh):
    """公開源の新しい情報を採用し、明示的に補完済みの読者情報を保持する。"""
    merged = dict(fresh)
    merged.pop('series', None)
    if fresh.get('k') == '記事':
        series = validated_series(fresh.get('series')) or validated_series(previous.get('series'))
        if series:
            merged['series'] = series
    if merged.get('a', 'unspecified') == 'unspecified' and previous.get('a') in AUDIENCES - {'unspecified'}:
        merged['a'] = previous['a']
        if previous.get('audience_source'):
            merged['audience_source'] = previous['audience_source']
    if not merged.get('d'):
        merged['d'] = previous.get('d', '')
    if not merged.get('group') and previous.get('group'):
        merged['group'] = previous['group']
        if previous.get('group_source'):
            merged['group_source'] = previous['group_source']
    merged['tags'] = clean_tags(merged.get('tags', []) + previous.get('tags', []))
    # 編集済み検索語等は更新元にない場合も失わない。原稿本文は取り込まない。
    if previous.get('aliases'):
        merged['aliases'] = clean_tags(merged.get('aliases', []) + previous['aliases'])
    return merged


def corpus_records(corpus, published):
    """URLの公開確認と、AtomPub由来の明示的な draft=no の両方を必須にする。"""
    out = []
    for item in corpus:
        if item.get('draft') != 'no' or item.get('url') not in published or not item.get('title'):
            continue
        title, tags = clean_text(item['title']), clean_tags(item.get('categories') or [])
        out.append({'t': title, 'u': item['url'], 'k': '記事', 'a': audience(title, tags),
                    'd': item.get('published', '')[:10], 'tags': tags})
    return out


def inherit_audiences(records):
    """公開マニフェストが結び付けた資料へ、元記事の明示的な対象読者を継承する。"""
    changed = 0
    for record in records.values():
        source = records.get(record.get('group', ''))
        if ((record.get('a') == 'unspecified' or record.get('audience_source') == record.get('group'))
                and source and source.get('k') == '記事'
                and source.get('a') in AUDIENCES - {'unspecified'}):
            changed += record.get('a') != source['a']
            record['a'] = source['a']
            record['audience_source'] = record['group']
    return changed


def infer_media_groups(records):
    """同一の公開slugで、明示された元記事が一意に一致する資料だけを結び付ける。"""
    by_slug = {}
    missing = []
    for record in records.values():
        if record.get('k') not in {'図解', 'スライド'}:
            continue
        parsed = urlparse(record['u'])
        match = re.fullmatch(r'/(?:infographics|slides)/([a-zA-Z0-9_-]+)/', parsed.path)
        if parsed.netloc != urlparse(TOOLS).netloc or not match:
            continue
        slug = match.group(1)
        if record.get('group') in records and records[record['group']].get('k') == '記事':
            by_slug.setdefault(slug, {}).setdefault(record['group'], record['u'])
        elif not record.get('group'):
            missing.append((slug, record))
    changed = 0
    for slug, record in missing:
        sources = by_slug.get(slug, {})
        if len(sources) == 1:
            record['group'], record['group_source'] = next(iter(sources.items()))
            changed += 1
    return changed


class ArticleMetadataParser(HTMLParser):
    """本文・サイドバーを読者分類に使わず、記事ヘッダーの公開カテゴリーだけを読む。"""
    def __init__(self):
        super().__init__()
        self.canonical, self.title, self.categories = '', '', []
        self.in_header, self.header_seen, self.capture, self.buffer = False, False, None, ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs.get('href', '')
        if tag == 'header' and 'entry-header' in classes and not self.header_seen:
            self.in_header = self.header_seen = True
        if self.in_header and tag == 'a':
            if 'entry-category-link' in classes and attrs.get('href', '').startswith(BLOG + '/archive/category/'):
                self.capture, self.buffer = 'category', ''
            elif 'entry-title-link' in classes:
                self.capture, self.buffer = 'title', ''

    def handle_data(self, data):
        if self.capture:
            self.buffer += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.capture:
            if self.capture == 'category':
                self.categories.append(clean_text(self.buffer))
            else:
                self.title = clean_text(self.buffer)
            self.capture, self.buffer = None, ''
        if tag == 'header':
            self.in_header = False


def fetch_article_metadata(record):
    """1回だけ再試行し、メタデータ以外の取得内容を返却・保存しない。"""
    for attempt in range(2):
        try:
            request = Request(record['u'], headers={'User-Agent': 'IchisouzoCatalog/2.0'})
            with urlopen(request, timeout=20) as response:
                body = response.read(4 * 1024 * 1024 + 1)
            if len(body) > 4 * 1024 * 1024:
                return None
            parser = ArticleMetadataParser()
            parser.feed(body.decode('utf-8'))
            if parser.canonical != record['u'] or not parser.header_seen or not parser.title:
                return None
            tags = clean_tags(parser.categories)
            return {'t': parser.title, 'u': record['u'], 'k': '記事',
                    'a': audience(parser.title, tags), 'd': record.get('d', ''), 'tags': tags}
        except (URLError, TimeoutError, OSError, UnicodeError):
            if attempt:
                return None


def complete_audiences(records, workers=5, limit=0):
    candidates = [record for record in records.values() if record.get('k') == '記事' and record.get('a') == 'unspecified']
    if limit:
        candidates = candidates[:limit]
    summary = {'updated': datetime.now(timezone.utc).isoformat(), 'scope': 'public_article_header_categories', 'checked': len(candidates),
               'classified': 0, 'no_explicit_audience': 0, 'failed': 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for previous, fresh in zip(candidates, pool.map(fetch_article_metadata, candidates)):
            if fresh is None:
                summary['failed'] += 1
                continue
            summary['classified' if fresh['a'] != 'unspecified' else 'no_explicit_audience'] += 1
            records[fresh['u']] = merge_record(previous, fresh)
    return summary

def rss_records(xml):
    out = []
    for item in ET.fromstring(xml).findall('./channel/item'):
        title, url = clean_text(item.findtext('title', '')), item.findtext('link', '')
        if not url.startswith(BLOG + '/entry/'):
            continue
        cats = clean_tags([x.text or '' for x in item.findall('category')])
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
        title = clean_text(item['title'])
        tags = clean_tags(item.get('tags', []) + [item.get('audience', ''), item.get('subtitle', '')])
        url = TOOLS + ('/infographics/' if kind == '図解' else '/slides/') + slug + '/'
        record = {'t': title, 'u': url, 'k': kind, 'a': audience(title, tags, item.get('audience', '')), 'd': item.get('date') or item.get('published_date', ''), 'tags': tags}
        # マニフェストの個人用/外部URLを、記事のグループキーへ流し込まない。
        blog_url = item.get('blog_url', '')
        record['group'] = blog_url if blog_url.startswith(BLOG + '/entry/') else ''
        if kind == '図解':
            set_card_image(record, slug)
        if item.get('slide_count'):
            record['pages'] = item['slide_count']
        out.append(record)
        video = item.get('youtube_id', '')
        if re.fullmatch(r'[\w-]{11}', video):
            out.append({'t': title, 'u': 'https://www.youtube.com/watch?v=' + video, 'k': '動画', 'a': record['a'], 'd': record['d'], 'tags': tags, 'img': 'https://i.ytimg.com/vi/' + video + '/hqdefault.jpg', 'group': record['group']})
    return out

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, help='公開サイトマップにあるURLのメタデータだけを補完')
    parser.add_argument('--complete-audience', action='store_true', help='未分類の公開記事から明示的なカテゴリーを補完')
    parser.add_argument('--audience-workers', type=int, choices=range(1, 7), default=5, help='記事取得の並列数（最大6）')
    parser.add_argument('--audience-limit', type=int, default=0, help='記事補完数の上限。0はすべての未分類記事')
    args = parser.parse_args()
    if args.audience_limit < 0:
        parser.error('--audience-limit は0以上にしてください')
    urls = [BLOG + '/rss', TOOLS + '/infographics/manifest.json', TOOLS + '/slides/manifest.json', TOOLS + '/', BLOG + '/sitemap.xml']
    with ThreadPoolExecutor(max_workers=5) as pool:
        rss, ig, slides, tool_html, sitemap = list(pool.map(fetch, urls))
        sitemap_root = ET.fromstring(sitemap)
        submaps = [x.text for x in sitemap_root.iter() if x.tag.endswith('loc') and x.text and x.text.startswith(BLOG + '/sitemap')]
        maps = list(pool.map(fetch, submaps))
    if sitemap_root.tag.endswith('urlset'):
        maps.append(sitemap)
    if not maps:
        raise RuntimeError('公開サイトマップを取得できません。既存カタログを保持します。')
    published = {x.text for xml in maps for x in ET.fromstring(xml).iter() if x.tag.endswith('loc') and x.text and x.text.startswith(BLOG + '/entry/')}
    if not published:
        raise RuntimeError('公開記事が0件。既存カタログを保持します。')
    fresh = rss_records(rss)
    # RSSに載った最新の公開記事は、サイトマップの更新待ちでも公開確認済み。
    published.update(record['u'] for record in fresh)
    old = json.loads((ROOT / 'search-index.json').read_text(encoding='utf-8'))
    old_by_url = {record['u']: record for record in old}
    before = Counter(record.get('a', 'unspecified') for record in old)
    records = {x['u']: x for x in old if x.get('k') == '記事' and x.get('u') in published}
    if args.corpus:
        for record in corpus_records(json.loads(args.corpus.read_text(encoding='utf-8')), published):
            records[record['u']] = merge_record(records.get(record['u'], {}), record)
    parser = ToolParser()
    parser.feed(tool_html)
    if not fresh or not parser.items:
        raise RuntimeError('RSSまたはツール一覧が空です。既存カタログを保持します。')
    ig_data = json.loads(ig)
    fresh += parser.items + manifest_records(ig_data, '図解') + manifest_records(json.loads(slides), 'スライド')
    for record in fresh:
        previous = records.get(record['u'], old_by_url.get(record['u'], {}))
        records[record['u']] = merge_record(previous, record)
        source = records.get(record.get('group', ''))
        if (record.get('a') == 'unspecified' and source and source.get('k') == '記事'
                and source.get('a') == records[record['u']].get('a') and source.get('a') != 'unspecified'):
            records[record['u']]['audience_source'] = record['group']
    for entry in ig_data.get('items', []):
        if entry.get('blog_url') in records and re.fullmatch(r'[a-zA-Z0-9_-]+', entry.get('slug', '')):
            set_card_image(records[entry['blog_url']], entry['slug'])
    for record in records.values():
        if record.get('a') == 'unspecified':
            record['a'] = audience(record['t'], record.get('tags', []))
    grouped = infer_media_groups(records)
    audit = complete_audiences(records, args.audience_workers, args.audience_limit) if args.complete_audience else None
    inherited = inherit_audiences(records)
    series_path = ROOT / 'scripts' / 'series_metadata.json'
    series_metadata = json.loads(series_path.read_text(encoding='utf-8')) if series_path.exists() else {}
    series_applied = apply_series_metadata(records, series_metadata, published)
    for record in records.values():
        record['t'] = clean_text(record['t'])
        record.setdefault('a', 'unspecified')
        record['tags'] = clean_tags(record.get('tags', []))
        record.setdefault('d', '')
        series = validated_series(record.get('series')) if record.get('k') == '記事' else None
        record.pop('series', None)
        if series:
            record['series'] = series
        if record.get('group') and record['group'] not in published:
            record['group'] = ''
            record.pop('audience_source', None)
        replace_legacy_image(record)
    ordered = sorted(records.values(), key=lambda r: r.get('d', ''), reverse=True)
    # 全取得・解析が完了してから書込。通信失敗で正常データを空にしない。
    (ROOT / 'search-index.json').write_text(json.dumps(ordered, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    after = Counter(record['a'] for record in ordered)
    meta = {'updated': datetime.now(timezone.utc).isoformat(), 'items': len(ordered), 'sources': urls,
            'audiences': dict(after), 'series_articles': dict(Counter(record['series']['id'] for record in ordered if record.get('series')))}
    previous_meta = json.loads((ROOT / 'catalog-meta.json').read_text(encoding='utf-8'))
    if audit or previous_meta.get('audience_audit'):
        meta['audience_audit'] = audit or previous_meta['audience_audit']
    (ROOT / 'catalog-meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Updated {len(ordered)} public records; {len(published)} sitemap URLs checked')
    print(f'Audience counts: before={dict(before)}, after={dict(after)}, source article inherited={inherited}')
    print(f'Exact public slug associations supplemented={grouped}')
    print(f'Verified public article series applied={series_applied}')
    if audit:
        print(f'Public article metadata audit: {audit}')

if __name__ == '__main__':
    main()
