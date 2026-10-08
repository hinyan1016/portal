"""新トップページの実操作・境界条件を検証する。"""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'improvements-20261004'
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
            requested = []
            page.on('request', lambda r: requested.append(r.url))
            for width in [1440, 1024, 768, 390, 320]:
                page.set_viewport_size({'width': width, 'height': 950 if width > 680 else 844})
                page.goto(base, wait_until='networkidle')
                # スマホは1列なので最初の表示を6件にする。
                expect(page.locator('.content-card')).to_have_count(6 if width <= 680 else 9)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                # 画像を実際に遅延読込した後で確認する。
                for img in page.locator('main img').all():
                    img.scroll_into_view_if_needed()
                page.wait_for_function("Array.from(document.querySelectorAll('main img')).every(x=>x.complete && x.naturalWidth>0)")
                # 図解は thumbs/ の軽量版だけを読み、原寸PNG（1枚約2MB）と帯状の thumb.png は読まない。
                assert not [u for u in requested if u.endswith('/infographic.png') or u.endswith('/thumb.png')], width
                assert any('/thumbs/' in u and u.endswith('.webp') for u in requested), width
                fonts = [u for u in requested if u.startswith('https://fonts.googleapis.com/')]
                assert fonts and all('Noto+Serif+JP' in u and 'text=' in u and 'Noto+Sans+JP' not in u for u in fonts), fonts
                requested.clear()
                if width <= 900:
                    page.locator('.menu-button').click()
                    expect(page.locator('#global-nav')).to_be_visible()
                    page.keyboard.press('Escape')
                    expect(page.locator('.menu-button')).to_have_attribute('aria-expanded', 'false')
                page.evaluate('scrollTo(0,0)')
                page.screenshot(path=str(OUT / f'preview-{width}.png'), full_page=True)
                report.append({'viewport':width, 'horizontal_overflow':False, 'all_visible_images_decoded':True})
                page.goto(base + 'guide.html', wait_until='networkidle')
                expect(page.locator('#guide-title')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), ('guide', width)
                assert page.locator('a[href="./?audience=general#library"]').count() == 1
                assert page.locator('a[href="./?audience=professional#library"]').count() == 1
                page.screenshot(path=str(OUT / f'guide-{width}.png'), full_page=True)
                report.append({'guide_viewport':width, 'horizontal_overflow':False})
            page.goto(base + '?q=もの忘れ#library', wait_until='networkidle')
            expect(page.locator('#result-status')).to_contain_text('4テーマ（7コンテンツ）')
            expect(page.locator('.content-card')).to_have_count(4)
            assert page.locator('.format-link').count() == 7
            page.screenshot(path=str(OUT / 'search-mobile.png'), full_page=True)
            page.goto(base + '?series=body-mysteries#library', wait_until='networkidle')
            expect(page.locator('.series-start')).to_have_attribute('href', 'https://blog.ichisouzo-lab.com/entry/2026/04/01/230038')
            assert page.locator('.series-episode').all_text_contents() == ['からだの不思議 第' + str(n) + '回' for n in range(1, 7)]
            assert page.locator('.series-next').first.get_attribute('href') == 'https://blog.ichisouzo-lab.com/entry/2026/04/02/192008'
            for _ in range(3):
                page.locator('#load-more').click()
            assert page.locator('.series-episode').count() == 19
            expect(page.locator('#load-more')).to_be_hidden()
            assert page.locator('.series-next').count() == 18
            page.goto(base + 'guide.html', wait_until='networkidle')
            page.locator('#guide-theme-toggle').click()
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            page.reload(wait_until='networkidle')
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            page.screenshot(path=str(OUT / 'guide-dark-mobile.png'), full_page=True)
            page.locator('#guide-theme-toggle').click()
            report.append({'real_catalog_alias_and_grouping':True, 'body_series_all_19_in_order':True, 'guide_theme_persistence':True})
            page.set_viewport_size({'width':1440, 'height':1000})
            page.goto(base, wait_until='networkidle')
            # ヒーローの候補語と検索窓は、下の一覧に新しい検索として結果を出す。JavaScriptが無い場合は ?q= のリンク。
            assert page.locator('#hero-chips a').first.get_attribute('href') == './?q=%E9%A0%AD%E7%97%9B#library'
            page.locator('[data-audience="general"]').click()
            page.locator('#hero-chips [data-query="頭痛"]').click()
            expect(page.locator('#result-status')).to_contain_text('「頭痛」')
            expect(page.locator('#site-search')).to_have_value('頭痛')
            expect(page.locator('[data-audience="all"]')).to_have_attribute('aria-pressed', 'true')
            assert 'q=' in page.url and page.locator('.content-card').count() >= 1
            page.locator('#hero-q').fill('めまい')
            page.locator('#hero-search button').click()
            expect(page.locator('#result-status')).to_contain_text('「めまい」')
            assert page.locator('.content-card').count() >= 1
            page.go_back(wait_until='networkidle')
            expect(page.locator('#hero-q')).to_have_value('頭痛')
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
