"""トップの画像、2周以上の再生、動きを抑える設定を実ブラウザーで確認する。"""
import functools
import http.server
import io
import json
from pathlib import Path
import sys
import threading
from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    server = None
    if len(sys.argv) > 1:
        base = sys.argv[1]
        prefix = 'public'
    else:
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
            functools.partial(QuietHandler, directory=str(ROOT / '_site')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/'
        prefix = 'local'
    results = []
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(reduced_motion='no-preference')
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            for width in [1440, 768, 390, 320]:
                page.set_viewport_size({'width': width, 'height': 900})
                page.goto(base, wait_until='domcontentloaded')
                page.wait_for_function("document.querySelector('.hero-art img').complete && document.querySelector('.hero-art img').naturalWidth > 0")
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                art = page.locator('.hero-art img')
                state = art.evaluate('(x)=>({src:x.currentSrc,width:x.naturalWidth,height:x.naturalHeight})')
                assert state['src'].endswith('/assets/hero-ai-knowledge.gif'), state
                assert state['width'] == 576 and state['height'] == 384
                page.screenshot(path=str(OUT / f'{prefix}-{width}.png'))
                results.append({'viewport_width': width, 'overflow': False, **state})
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(base, wait_until='domcontentloaded')
            art = page.locator('.hero-art img')
            art.wait_for()
            # 再生開始から6秒を過ぎても絵が変わることを検証（GIFは5秒）。
            page.wait_for_timeout(6100)
            a = Image.open(io.BytesIO(art.screenshot())).convert('RGB')
            page.wait_for_timeout(1250)
            b = Image.open(io.BytesIO(art.screenshot())).convert('RGB')
            difference = ImageStat.Stat(ImageChops.difference(a, b)).mean
            assert max(difference) > .05, difference
            results.append({'animation_after_first_loop': True, 'mean_rgb_difference': difference})
            page.emulate_media(reduced_motion='reduce')
            page.reload(wait_until='domcontentloaded')
            page.wait_for_function("document.querySelector('.hero-art img').complete && document.querySelector('.hero-art img').naturalWidth > 0")
            reduced = page.locator('.hero-art img').evaluate('(x)=>x.currentSrc')
            assert reduced.endswith('/assets/hero-ai-knowledge.webp'), reduced
            results.append({'reduced_motion_static_image': True, 'src': reduced})
            assert not errors, errors
            browser.close()
        report = {'base': base, 'checks': results, 'javascript_errors': errors}
        (OUT / f'{prefix}-qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))
    finally:
        if server:
            server.shutdown()


if __name__ == '__main__':
    main()
