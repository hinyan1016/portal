"""スマホ幅で下の3節（オフライン版・制作こぼれ話・About）が要点表示になり、ボタンとページ内リンクで開くことを実Chromiumで検証。"""
import argparse
import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ('offline', 'columns', 'about')
# 畳んだときに隠れる代表の要素（節ごとに1つ）
HIDDEN = {'offline': '#offline .download-cards', 'columns': '#columns .column-grid > .column-card:nth-child(2)', 'about': '#about .about-details'}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def heights(pg):
    return pg.evaluate("(ids) => ids.map(function (id) { return Math.round(document.getElementById(id).getBoundingClientRect().height); })", list(SECTIONS))


def overflow(pg):
    return pg.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')


def open_page(browser, base, width, errors, **kw):
    mobile = width < 700
    ctx = browser.new_context(viewport={'width': width, 'height': 844 if mobile else 900}, is_mobile=mobile, has_touch=mobile, reduced_motion='reduce', **kw)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errors.append(str(e)))
    return ctx, pg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url')
    a = ap.parse_args()
    server = None
    if a.url:
        base = a.url.rstrip('/') + '/'
    else:
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:' + str(server.server_port) + '/'
    report = {'status': 'PASS', 'widths': [], 'checks': []}
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for width in (390, 320):
                ctx, pg = open_page(browser, base, width, errors)
                pg.goto(base, wait_until='networkidle')
                pg.wait_for_selector('.content-card')
                closed = heights(pg)
                for name in SECTIONS:
                    button = pg.locator('#' + name + ' .fold-toggle')
                    assert button.count() == 1 and button.is_visible(), (width, name)
                    assert button.get_attribute('aria-expanded') == 'false', (width, name)
                    assert 'タップで開閉' in button.inner_text(), (width, name)
                    assert not pg.locator(HIDDEN[name]).first.is_visible(), (width, name)
                assert not overflow(pg), width
                for name in SECTIONS:
                    button = pg.locator('#' + name + ' .fold-toggle')
                    before = button.inner_text()
                    button.click()
                    assert button.get_attribute('aria-expanded') == 'true', (width, name)
                    assert pg.locator(HIDDEN[name]).first.is_visible(), (width, name)
                    assert button.inner_text() != before, (width, name)
                opened = heights(pg)
                assert not overflow(pg), width
                # 要点表示は、全部開いたときの6割以下の長さに収まる。
                assert sum(closed) <= sum(opened) * 0.6, (width, closed, opened)
                for name in SECTIONS:
                    button = pg.locator('#' + name + ' .fold-toggle')
                    button.click()
                    assert button.get_attribute('aria-expanded') == 'false', (width, name)
                    assert not pg.locator(HIDDEN[name]).first.is_visible(), (width, name)
                assert heights(pg) == closed, width
                # キーボードでも開ける。
                pg.locator('#about .fold-toggle').focus()
                pg.keyboard.press('Enter')
                assert pg.locator(HIDDEN['about']).is_visible(), width
                report['widths'].append({'width': width, 'closed': closed, 'opened': opened})
                ctx.close()
            report['checks'] += ['要点表示と開閉', '文言の切り替え', '横はみ出しなし', 'キーボード操作']

            # ページ内リンクの飛び先が畳んだ中にあれば、開いて飛び先を画面の上に出す。
            ctx, pg = open_page(browser, base, 390, errors)
            pg.goto(base, wait_until='networkidle')
            archived = pg.evaluate("(function () { var card = document.querySelector('#columns .columns-archive .column-card'); return card ? card.id : ''; })()")
            second = pg.evaluate("(function () { var card = document.querySelector('#columns .column-grid > .column-card:nth-child(2)'); return card ? card.id : ''; })()")
            ctx.close()
            targets = [('offline', HIDDEN['offline']), ('about', HIDDEN['about'])]
            if second:
                targets.append((second, '#' + second))
            if archived:
                targets.append((archived, '#' + archived))
            for target, must_show in targets:
                ctx, pg = open_page(browser, base, 390, errors)
                pg.goto(base + '#' + target, wait_until='networkidle')
                pg.wait_for_timeout(400)
                assert pg.locator(must_show).first.is_visible(), target
                top = pg.evaluate("(id) => Math.round(document.getElementById(id).getBoundingClientRect().top)", target)
                assert 0 <= top <= 140, (target, top)
                ctx.close()
            # 開いたままのページでリンクを踏んだとき（hashchange）も同じ。
            ctx, pg = open_page(browser, base, 390, errors)
            pg.goto(base, wait_until='networkidle')
            pg.evaluate("location.hash = '#about'")
            pg.wait_for_timeout(400)
            assert pg.locator(HIDDEN['about']).is_visible()
            ctx.close()
            report['checks'].append('ページ内リンクで開いて着地')

            # PC幅ではボタンを出さず、全部表示のまま。
            for width in (768, 1440):
                ctx, pg = open_page(browser, base, width, errors)
                pg.goto(base, wait_until='networkidle')
                for name in SECTIONS:
                    assert not pg.locator('#' + name + ' .fold-toggle').is_visible(), (width, name)
                    assert pg.locator(HIDDEN[name]).first.is_visible(), (width, name)
                ctx.close()
            report['checks'].append('PC幅は全部表示')

            # JavaScriptが無効でも、スマホ幅で全部読める（ボタンは出ない）。
            ctx, pg = open_page(browser, base, 390, errors, java_script_enabled=False)
            # load まで待つ。JavaScript無効だと domcontentloaded は styles.css の適用前に来ることがあり、
            # ボタンを隠す指定がまだ効いていない画面を判定してしまう（公開URL相手で時々失敗した）。
            pg.goto(base, wait_until='load')
            for name in SECTIONS:
                assert not pg.locator('#' + name + ' .fold-toggle').is_visible(), name
                assert pg.locator(HIDDEN[name]).first.is_visible(), name
            ctx.close()
            report['checks'].append('JavaScript無効時は全部表示')
            browser.close()
        assert not errors, errors
    finally:
        if server:
            server.shutdown()
            server.server_close()
    report['runtime_errors'] = errors
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
