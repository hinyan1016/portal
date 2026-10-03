"""テーマ整理・表記ゆれ・シリーズ順・URL単位の保存を実ブラウザーで検証する。"""
import functools
import http.server
import json
from pathlib import Path
import threading
from urllib.parse import quote

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
FEEDS = [
    'https://blog.ichisouzo-lab.com/rss',
    'https://tools.ichisouzo-lab.com/infographics/manifest.json',
    'https://tools.ichisouzo-lab.com/slides/manifest.json',
]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def article(slug, title, **kwargs):
    return {'t': title, 'u': f'https://blog.ichisouzo-lab.com/entry/{slug}',
            'k': '記事', 'a': 'general', 'd': '2026-10-01', **kwargs}


def run():
    memory = article('memory', '物忘れの受診相談', aliases=['名前が出ない'], summary='受診について考えるための記事です。')
    fixtures = [memory,
        {'t': '記憶の動画', 'u': 'https://www.youtube.com/watch?v=memory00001', 'k': '動画', 'a': 'unspecified', 'group': memory['u'], 'img': 'https://i.ytimg.com/vi/memory00001/hqdefault.jpg'},
        {'t': '記憶の図解', 'u': 'https://tools.ichisouzo-lab.com/infographics/memory/', 'k': '図解', 'a': 'unspecified', 'group': memory['u']},
        {'t': '記憶の専門資料', 'u': 'https://tools.ichisouzo-lab.com/slides/memory-pro/', 'k': 'スライド', 'a': 'professional', 'group': memory['u']},
        article('numbness', '痺れを整理する'), article('dizziness', '眩暈を整理する'), article('seizure', '痙攣を整理する'),
        article('lev', 'レベチラセタムの解説'), article('levodopa', 'levodopaの解説'),
        article('ssri', '選択的セロトニン再取り込み阻害薬について'),
        article('ssri-boundary', 'ssrifyという別の単語について'),
        article('nsaid', '非ステロイド性抗炎症薬について'),
        article('distinct-1', '同じ見出しの解説'), article('distinct-2', '同じ見出しの解説'),
        article('entities', 'A &amp;amp; B &quot;引用&quot; &lt;img src=x onerror=alert(1)&gt;'),
        {'t': 'Unsafe', 'u': 'javascript:alert(1)', 'k': '記事'},
    ]
    for number in [3, 1, 2]:
        episode = article(f'anti-{number}', f'テーマ{number}（医師が採点するアンチエイジング 第{number}回）')
        fixtures.append(episode)
        fixtures.append({'t': f'動画{number}', 'u': f'https://www.youtube.com/watch?v=antiaging0{number}', 'k': '動画', 'a': 'general', 'group': episode['u']})
    fixtures.append(article('anti-overview', 'アンチエイジングの全体像'))
    fixtures.append({'t': '医師が採点するアンチエイジング 第1回', 'u': 'https://tools.ichisouzo-lab.com/slides/unlinked-series/', 'k': 'スライド', 'a': 'general'})
    for number in [17, 2, 1]:
        fixtures.append(article(f'body-{number}', f'からだのテーマ{number}' if number == 1 else f'からだのテーマ{number}【からだの不思議 #{number}】', **({'series': {'id': 'body-mysteries', 'number': 1}} if number == 1 else {})))

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            context.route('https://**', lambda route: route.abort())
            for url in FEEDS:
                context.route(url, lambda route: route.abort())
            # 新着RSSに任意メタデータが無くても、確認済みの別名・説明・回番号を失わない。
            rss = '<rss><channel><item><title>物忘れの受診相談</title><link>' + memory['u'] + '</link><pubDate>Thu, 01 Oct 2026 00:00:00 +0900</pubDate></item><item><title>からだのテーマ1</title><link>https://blog.ichisouzo-lab.com/entry/body-1</link><pubDate>Thu, 01 Oct 2026 00:00:00 +0900</pubDate></item></channel></rss>'
            context.route(FEEDS[0], lambda route: route.fulfill(content_type='application/rss+xml', body=rss))
            context.route('**/search-index.json', lambda route: route.fulfill(json=fixtures))
            context.route('https://i.ytimg.com/vi/memory00001/hqdefault.jpg', lambda route: route.fulfill(content_type='image/svg+xml', body='<svg xmlns="http://www.w3.org/2000/svg" width="120" height="90"><rect width="120" height="90" fill="gray"/></svg>'))
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))

            def search(query):
                page.goto(base + '?q=' + quote(query), wait_until='networkidle')
                expect(page.locator('#result-status')).to_contain_text('テーマ')

            for japanese, variant in [('物忘れ', 'もの忘れ'), ('痺れ', 'しびれ'), ('眩暈', 'めまい'), ('痙攣', 'けいれん')]:
                search(japanese)
                canonical = page.locator('#content-grid .card-link').evaluate_all('links => links.map(link => link.href)')
                search(variant)
                assert canonical == page.locator('#content-grid .card-link').evaluate_all('links => links.map(link => link.href)'), variant
                assert len(canonical) == 1
            for query, expected in [('LEV', '/entry/lev'), ('SSRI', '/entry/ssri'), ('NSAID', '/entry/nsaid')]:
                search(query)
                expect(page.locator('.content-card')).to_have_count(1)
                assert page.locator('.card-link').get_attribute('href').endswith(expected)
                if query == 'SSRI':
                    page.locator('[data-topic="薬・治療"]').click()
                    expect(page.locator('.content-card')).to_have_count(1)
            search('levodopa')
            expect(page.locator('.content-card')).to_have_count(1)
            assert page.locator('.card-link').get_attribute('href').endswith('/entry/levodopa')

            # タイトルが異なる関連形式も、検証済みの元記事URLによって一つにまとめる。
            search('名前が出ない')
            expect(page.locator('.content-card')).to_have_count(1)
            expect(page.locator('.format-option')).to_have_count(4)
            expect(page.locator('#result-status')).to_contain_text('1テーマ（4コンテンツ）')
            expect(page.locator('.card-summary')).to_contain_text('受診について')
            expect(page.locator('.card-media .media-art')).to_have_count(1)
            expect(page.locator('.card-media img')).to_have_count(0)
            video = 'https://www.youtube.com/watch?v=memory00001'
            page.locator(f'[data-save="{video}"]').click()
            expect(page.locator('#saved-count')).to_have_text('1')
            page.reload(wait_until='networkidle')
            expect(page.locator(f'[data-save="{video}"]')).to_have_attribute('aria-pressed', 'true')
            page.locator('[data-audience="general"]').click()
            expect(page.locator('.format-option')).to_have_count(3)
            assert page.locator('.format-link[href$="/slides/memory-pro/"]').count() == 0
            page.locator('[data-kind="動画"]').click()
            expect(page.locator('.content-card')).to_have_count(1)
            expect(page.locator('#result-status')).to_contain_text('1件')
            page.route(video, lambda route: route.fulfill(body='<html>動画の移動先</html>'))
            page.locator('.card-link').click()
            page.wait_for_url(video)
            page.go_back(wait_until='networkidle')
            page.locator('#open-collection').click()
            page.locator('[data-collection="recent"]').click()
            expect(page.locator('.collection-item a')).to_have_attribute('href', video)
            page.keyboard.press('Escape')

            search('同じ見出し')
            expect(page.locator('.content-card')).to_have_count(2)
            search('A & B')
            expect(page.locator('.content-card')).to_have_count(1)
            expect(page.locator('.content-card h3')).to_have_text('A & B "引用" <img src=x onerror=alert(1)>')
            assert page.locator('[onerror]').count() == 0
            assert page.locator('a[href^="javascript:"]').count() == 0

            for series, numbers in [('anti-aging', [1, 2, 3]), ('body-mysteries', [1, 2, 17])]:
                page.goto(base + '?series=' + series, wait_until='networkidle')
                expect(page.locator('#series-navigation')).to_be_visible()
                expect(page.locator('.content-card')).to_have_count(3)
                actual = page.locator('.series-episode').all_text_contents()
                assert all(f'第{number}回' in text for number, text in zip(numbers, actual)), actual
                expect(page.locator('.series-start')).to_have_attribute('href', fixtures[next(i for i, item in enumerate(fixtures) if item.get('k') == '記事' and item['u'].endswith('anti-1' if series == 'anti-aging' else 'body-1'))]['u'])
                next_links = page.locator('.series-next').all_text_contents()
                assert len(next_links) == (2 if series == 'anti-aging' else 1), next_links
                page.evaluate('navigator.clipboard.writeText = async text => { window.copiedURL = text; }')
                page.locator('#share-search').click()
                page.wait_for_function('Boolean(window.copiedURL)')
                assert 'series=' + series in page.evaluate('window.copiedURL')
                page.locator('[data-clear-series]').click()
                expect(page.locator('#series-navigation')).to_be_hidden()
                page.go_back(wait_until='networkidle')
                expect(page.locator('#series-navigation')).to_be_visible()
                expect(page.locator('.content-card')).to_have_count(3)
            assert not errors, errors
            browser.close()
        print(json.dumps({'status': 'PASS', 'checks': ['Japanese variants', 'bounded medicine abbreviations', 'group-by-article only', 'format links and saves', 'audience inheritance', 'known professional asset excluded under general filter', 'kind filtering', 'original URL history', 'safe entity decoding', 'YouTube HTTP200 placeholder fallback', 'numbered series order from title and verified metadata', 'metadata retained across RSS refresh', 'no skipped episode next', 'series URL sharing and Back'], 'runtime_errors': errors}, ensure_ascii=False))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    run()
