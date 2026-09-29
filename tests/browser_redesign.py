"""新トップページの実操作・境界条件を検証する。"""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'redesign-20260929'
OUT.mkdir(exist_ok=True)
FEEDS = ['https://blog.ichisouzo-lab.com/rss', 'https://tools.ichisouzo-lab.com/infographics/manifest.json', 'https://tools.ichisouzo-lab.com/slides/manifest.json']

def run():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
    report = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # 保存済みカタログを使う再現可能な試験。別途、公開フィードの実測も行う。
            context = browser.new_context()
            for url in FEEDS:
                context.route(url, lambda r: r.abort())
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            for width in [1440, 1024, 768, 390, 320]:
                page.set_viewport_size({'width': width, 'height': 950 if width > 680 else 844})
                page.goto(base, wait_until='networkidle')
                expect(page.locator('.content-card')).to_have_count(9)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                # 画像を実際に遅延読込した後で確認する。
                for img in page.locator('main img').all():
                    img.scroll_into_view_if_needed()
                page.wait_for_function("Array.from(document.querySelectorAll('main img')).every(x=>x.complete && x.naturalWidth>0)")
                if width <= 900:
                    page.locator('.menu-button').click()
                    expect(page.locator('#global-nav')).to_be_visible()
                    page.keyboard.press('Escape')
                    expect(page.locator('.menu-button')).to_have_attribute('aria-expanded', 'false')
                page.evaluate('scrollTo(0,0)')
                page.screenshot(path=str(OUT / f'preview-{width}.png'), full_page=True)
                report.append({'viewport':width, 'horizontal_overflow':False, 'all_visible_images_decoded':True})
            page.set_viewport_size({'width':1440, 'height':1000})
            page.goto(base, wait_until='networkidle')
            page.locator('#load-more').click()
            expect(page.locator('.content-card')).to_have_count(18)
            page.locator('[data-audience="general"]').click()
            assert set(page.locator('.content-card').evaluate_all('xs=>xs.map(x=>x.dataset.reader)')) <= {'general','both'}
            page.locator('[data-kind="ツール"]').click()
            expect(page.locator('#empty-state')).to_be_visible()
            page.locator('#reset-filters').click()
            page.locator('#site-search').fill('頭痛')
            expect(page.locator('#result-status')).to_contain_text('頭痛')
            page.locator('[data-kind="ツール"]').click()
            result_count = page.locator('.content-card').count()
            assert result_count >= 1
            assert all('頭痛' in t for t in page.locator('.content-card h3').all_text_contents())
            url = page.url
            page.reload(wait_until='networkidle')
            expect(page.locator('#site-search')).to_have_value('頭痛')
            expect(page.locator('[data-kind="ツール"]')).to_have_attribute('aria-pressed','true')
            expect(page.locator('.content-card')).to_have_count(result_count)
            # コピーした検索条件が再現可能なURLになる。
            page.evaluate("navigator.clipboard.writeText = async text => { window.copiedURL=text; }")
            page.locator('#share-search').click()
            page.wait_for_function('Boolean(window.copiedURL)')
            assert 'kind=' in page.evaluate('window.copiedURL') and page.evaluate('window.copiedURL').endswith('#library')
            # しおり・再読込・モーダルのEscape・フォーカス復帰。
            page.locator('.save-button[data-save="https://tools.ichisouzo-lab.com/headache.html"]').click()
            expect(page.locator('#saved-count')).to_have_text('1')
            page.reload(wait_until='networkidle')
            expect(page.locator('#saved-count')).to_have_text('1')
            page.locator('#open-collection').click()
            expect(page.locator('.collection-item')).to_have_count(1)
            page.keyboard.press('Escape')
            expect(page.locator('#collection-dialog')).not_to_be_visible()
            expect(page.locator('#open-collection')).to_be_focused()
            # 実際にコンテンツを開いたときだけ履歴を追加する。
            page.route('https://tools.ichisouzo-lab.com/headache.html', lambda r: r.fulfill(body='<html><title>Test destination</title></html>'))
            page.locator('.card-link[href="https://tools.ichisouzo-lab.com/headache.html"]').click()
            page.wait_for_url('**/headache.html')
            page.go_back(wait_until='networkidle')
            page.locator('#open-collection').click()
            page.locator('[data-collection="recent"]').click()
            expect(page.locator('.collection-item')).to_have_count(1)
            page.locator('#clear-history').click()
            expect(page.locator('.collection-item')).to_have_count(0)
            page.locator('[data-collection="saved"]').click()
            page.locator('#collection-list .save-button').click()
            expect(page.locator('#saved-count')).to_have_text('0')
            page.keyboard.press('Escape')
            page.locator('#theme-toggle').click()
            expect(page.locator('html')).to_have_attribute('data-theme','dark')
            page.reload(wait_until='networkidle')
            expect(page.locator('html')).to_have_attribute('data-theme','dark')
            page.screenshot(path=str(OUT/'dark-mode.png'), full_page=True)
            page.locator('#reset-filters').click()
            page.locator('#sort-order').select_option('title')
            assert 'sort=title' in page.url
            page.locator('#site-search').fill('存在しないXYZ9999999')
            expect(page.locator('#empty-state')).to_be_visible()
            assert 'XYZ9999999' in page.locator('#fulltext-link').get_attribute('href')
            assert not errors, errors
            report.append({'search_filters_pagination':True,'url_roundtrip_and_share':True,'saved_persistence':True,'history_and_clear':True,'modal_escape_and_focus':True,'theme_persistence':True,'runtime_errors':errors})
            context.close()
            # 悪意あるフィード・壊れた保存領域・画像欠落。
            bad = browser.new_context()
            for feed in FEEDS:
                bad.route(feed, lambda r:r.abort())
            bad.add_init_script("localStorage.setItem('ichisouzo-saved','[null,{},42]');")
            bad.route('**/search-index.json', lambda r:r.fulfill(json=[
                {'t':'<img src=x onerror=alert(1)> 安全テスト','u':'https://blog.ichisouzo-lab.com/entry/safe','k':'記事','a':'general'},
                {'t':'危険テスト','u':'javascript:alert(1)','k':'記事'},
                {'t':'外部テスト','u':'https://evil.example/a','k':'記事'},
                {'t':'欠落した図解','u':'https://tools.ichisouzo-lab.com/infographics/test-missing/','k':'図解','img':'https://tools.ichisouzo-lab.com/infographics/test-missing/thumb.png','a':'general'},
                None, 42]))
            bad.route('**/test-missing/*.png',lambda r:r.fulfill(status=404))
            b = bad.new_page()
            b.goto(base, wait_until='networkidle')
            expect(b.locator('.content-card')).to_have_count(2)
            assert b.locator('[onerror]').count()==0
            assert b.locator('a[href^="javascript:"]').count()==0
            expect(b.locator('.card-media .media-art')).to_have_count(2)
            expect(b.locator('#saved-count')).to_have_text('0')
            bad.close()
            denied = browser.new_context()
            for feed in FEEDS: denied.route(feed,lambda r:r.abort())
            denied.add_init_script("Storage.prototype.setItem=function(){throw new Error('denied');};")
            d=denied.new_page();d.goto(base, wait_until='networkidle');d.locator('.save-button').first.click()
            expect(d.locator('#toast')).to_contain_text('保存できない')
            expect(d.locator('#saved-count')).to_have_text('1')
            denied.close()
            offline = browser.new_context()
            for feed in FEEDS: offline.route(feed,lambda r:r.abort())
            offline.route('**/search-index.json',lambda r:r.abort())
            off=offline.new_page();off.goto(base,wait_until='networkidle')
            expect(off.locator('#empty-state')).to_be_visible()
            expect(off.locator('#result-status')).to_contain_text('取得できません')
            offline.close()
            report.append({'unsafe_urls_excluded':True,'html_injection_escaped':True,'invalid_storage_ignored':True,'denied_storage_disclosed':True,'missing_image_fallback':True,'all_feeds_offline_fallback':True})
            browser.close()
        (OUT/'qa.json').write_text(json.dumps({'status':'PASS','checks':report},ensure_ascii=False,indent=2),encoding='utf-8')
        print('PASS: five viewports, search, filters, pagination, persistence, history, theme, URL sharing, keyboard, unsafe inputs, offline and missing images')
    finally:
        server.shutdown(); server.server_close()

if __name__=='__main__':run()
