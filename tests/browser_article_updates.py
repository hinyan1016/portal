"""実データを変更せず、両トップ・障害・狭幅・記事ページを確認。"""
import functools
import http.server
from pathlib import Path
import threading
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from article_updates import render
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}/'
snippet = (ROOT / 'docs/hatena-recent-updates-snippet.html').read_text(encoding='utf-8')
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://**/*', lambda r: r.abort())
        for width in (320, 390, 768, 1440):
            page.set_viewport_size(dict(width=width, height=900))
            page.goto(base)
            expect(page.locator('#recent-updates')).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('#recent-updates').screenshot(path=str(ROOT / 'docs' / f'updates-{width}.png'))
        fixture = render([dict(id=str(i), date='2026-10-12', title='検証用の長い記事名と説明文の折り返し確認' * 4, summary='変更点の説明です。' * 20, url='https://blog.ichisouzo-lab.com/entry/test', evidence='test-only', public_verified=True) for i in range(7)])
        page.set_viewport_size(dict(width=320, height=900))
        page.set_content('<html lang="ja"><style>'+(ROOT/'article-updates.css').read_text(encoding='utf-8')+'</style>'+fixture+'</html>')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.get_by_text('以前の更新を読む').click()
        expect(page.locator('details li')).to_have_count(2)
        page.locator('.ics-updates a').first.focus()
        assert page.locator('.ics-updates a').first.evaluate('el => el === document.activeElement')
        page.screenshot(path=str(ROOT/'docs/updates-test-fixture-320.png'), full_page=True)
        # 部品を実際に設置するホスト相当。実サイト管理画面は操作しない。
        blog = browser.new_context(viewport=dict(width=320, height=850))
        blog.route('https://blog.test/**', lambda r: r.fulfill(content_type='text/html', body='<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><body><nav>既存ナビ</nav>'+snippet+'<main>既存記事一覧</main></body></html>'))
        blog.route('https://ichisouzo-lab.com/article-updates-widget.js', lambda r: r.fulfill(content_type='text/javascript', body=(ROOT/'article-updates-widget.js').read_text(encoding='utf-8')))
        b = blog.new_page()
        b.goto('https://blog.test/')
        expect(b.locator('#recent-updates')).to_be_visible()
        assert b.evaluate('document.documentElement.scrollWidth <= innerWidth')
        b.screenshot(path=str(ROOT/'docs/updates-blog-320.png'))
        b.goto('https://blog.test/entry/example')
        expect(b.locator('#ics-updates-host')).to_be_hidden()
        blog.route('https://ichisouzo-lab.com/article-updates-widget.js', lambda r: r.abort())
        b.goto('https://blog.test/')
        expect(b.get_by_role('link', name='最近更新した記事の一覧を見る')).to_be_visible()
        nojs = browser.new_context(java_script_enabled=False)
        n = nojs.new_page()
        n.goto(base)
        expect(n.locator('#recent-updates')).to_be_visible()
        assert not errors, errors
        browser.close()
    print('PASS: widths 320/390/768/1440, both renderers, offline widget fallback, article guard, no-JS portal')
finally:
    server.shutdown()
