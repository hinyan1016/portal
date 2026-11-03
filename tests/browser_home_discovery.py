"""トップの導線・タブ・読者切り替えを、実カタログとブラウザーで検証する。"""
import argparse
from datetime import datetime, timezone
import functools
import http.server
import json
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def run(shots):
    shots.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
    report, errors = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(reduced_motion='reduce')
            # 更新時刻だけを固定し、表示試験中の外部フィード更新を避ける。実カタログは変更しない。
            context.route('**/catalog-meta.json', lambda route: route.fulfill(json={'updated': datetime.now(timezone.utc).isoformat()}))
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            for width in [1440, 1024, 768, 390, 320]:
                page.set_viewport_size({'width': width, 'height': 1000 if width > 680 else 844})
                page.goto(base, wait_until='networkidle')
                expect(page.locator('.content-card')).to_have_count(6 if width <= 680 else 9)
                page.evaluate('document.fonts.ready')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                metrics = page.evaluate('''() => ({width: innerWidth,
                    news: Math.round(document.querySelector('#medical-news-title').getBoundingClientRect().top + scrollY),
                    library: Math.round(document.querySelector('#library').getBoundingClientRect().top + scrollY)})''')
                if width <= 680:
                    assert metrics['news'] < 800 and metrics['library'] < 1600, metrics
                assert page.locator('#audience-filters').bounding_box()['y'] < metrics['news']
                page.screenshot(path=str(shots / f'home-{width}.png'))
                report.append(metrics)
                page.locator('#home-tab-updates').click()
                expect(page.locator('#home-panel-new')).to_be_hidden()
                expect(page.locator('#home-panel-updates')).to_be_visible()
                expect(page.locator('.home-updates-list li:visible')).to_have_count(3)
                page.locator('#home-tab-updates').focus()
                page.keyboard.press('End')
                expect(page.locator('#home-tab-picks')).to_be_focused()
                expect(page.locator('#home-panel-picks')).to_be_visible()
                for image in page.locator('#home-panel-picks img').all():
                    image.scroll_into_view_if_needed()
                page.wait_for_function("Array.from(document.querySelectorAll('#home-panel-picks img')).every(x => x.complete && x.naturalWidth > 0)")
                assert page.locator('#home-panel-picks img').count() == 3
                page.keyboard.press('ArrowRight')
                expect(page.locator('#home-tab-new')).to_be_focused()
                expect(page.locator('#home-panel-new')).to_be_visible()

            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(base, wait_until='networkidle')
            page.locator('[data-audience="general"]').click()
            expect(page.locator('#library-audience')).to_have_value('general')
            expect(page.locator('#home-tab-picks')).to_have_text('おすすめ1件')
            expect(page.locator('[data-discovery-route="assessment"]')).to_contain_text('症状チェック')
            expect(page.locator('[data-discovery-route="medication"]')).to_contain_text('図解で知る')
            assert 'audience=general' in page.locator('#hero-chips a').first.get_attribute('href')
            page.locator('#hero-q').fill('頭痛')
            page.locator('#hero-search button').click()
            expect(page.locator('#site-search')).to_have_value('頭痛')
            assert parse_qs(urlsplit(page.url).query)['audience'] == ['general']
            assert page.locator('.content-card').count() > 0
            assert set(page.locator('.content-card').evaluate_all('xs => xs.map(x => x.dataset.reader)')) <= {'general', 'both'}
            page.reload(wait_until='networkidle')
            expect(page.locator('[data-audience="general"]')).to_have_attribute('aria-pressed', 'true')
            page.locator('#library-audience').select_option('professional')
            expect(page.locator('[data-audience="professional"]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('#home-tab-picks')).to_have_text('おすすめ2件')
            page.go_back(wait_until='networkidle')
            expect(page.locator('#library-audience')).to_have_value('general')
            page.locator('#reset-filters').click()
            expect(page.locator('#hero-q')).to_have_value('')
            expect(page.locator('#library-audience')).to_have_value('all')
            page.locator('#home-tab-picks').click()
            page.locator('#medical-news').scroll_into_view_if_needed()
            page.screenshot(path=str(shots / 'recommendations-390.png'))
            page.locator('#home-tab-updates').click()
            page.locator('#medical-news').scroll_into_view_if_needed()
            page.screenshot(path=str(shots / 'updates-390.png'))
            page.locator('a.home-updates-more').click()
            expect(page.locator('#recent-updates h2')).to_have_text('最近更新した記事')
            assert page.locator('#recent-updates li').count() > 3

            # 既存の更新履歴アンカーを共有しても、隠れたタブへ飛ばない。
            page.goto(base + '#recent-updates', wait_until='networkidle')
            expect(page.locator('#home-tab-updates')).to_have_attribute('aria-selected', 'true')
            expect(page.locator('#recent-updates')).to_be_visible()
            for purpose in ['assessment', 'medication']:
                page.goto(base, wait_until='networkidle')
                page.locator(f'[data-discovery-route="{purpose}"]').click()
                expect(page.locator('[data-kind="ツール"]')).to_have_attribute('aria-pressed', 'true')
                expect(page.locator('#empty-state')).to_be_hidden()
                assert page.locator('.content-card').count() > 0
                report.append({'route': purpose, 'visible_results': page.locator('.content-card').count()})

            # 保存と形式別リンクは、コンパクト表示でも元のURLを保持する。
            page.goto(base, wait_until='networkidle')
            button = page.locator('#content-grid .save-button').first
            saved_url = button.get_attribute('data-save')
            button.click()
            expect(page.locator('#saved-count')).to_have_text('1')
            page.reload(wait_until='networkidle')
            page.locator('#open-collection').click()
            expect(page.locator(f'#collection-list a[href="{saved_url}"]')).to_be_visible()
            page.keyboard.press('Escape')
            page.locator('#theme-toggle').click()
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            page.screenshot(path=str(shots / 'dark-390.png'))
            page.locator('#library').scroll_into_view_if_needed()
            page.screenshot(path=str(shots / 'library-390.png'))
            for width in [1440, 390, 320]:
                page.set_viewport_size({'width': width, 'height': 1000})
                page.goto(base, wait_until='networkidle')
                page.evaluate("document.documentElement.style.fontSize = '32px'")
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), ('text-size-200%', width)

            nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
            n = nojs.new_page()
            n.goto(base, wait_until='networkidle')
            expect(n.locator('#home-feed-tabs')).to_be_hidden()
            for panel in ['new', 'updates', 'picks']:
                expect(n.locator('#home-panel-' + panel)).to_be_visible()
            assert n.locator('form#hero-search input[name="q"]').count() == 1
            assert n.locator('#home-panel-new a[href^="https://blog."]').count() >= 3
            assert not errors, errors
            browser.close()
        result = {'status': 'PASS', 'viewports_and_routes': report, 'runtime_errors': errors,
                  'checks': ['タブのクリックとキーボード操作', '読者の同期と検索への引継ぎ', 'URL復元・戻る',
                             '更新履歴アンカーと全履歴へのリンク', '目的別入口', '保存と配色の維持',
                             '文字200%で横はみ出しなし', 'JavaScript無効時の静的リンク']}
        (shots / 'qa.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False))
    finally:
        server.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--shots', type=Path, default=ROOT / 'tests/browser-artifacts/home-discovery')
    run(parser.parse_args().shots)
