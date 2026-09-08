"""Exercise missing thumbnails against live images, then total image failure."""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def main():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/'
    evidence = ROOT / 'docs' / 'image-fix-20260909'
    evidence.mkdir(exist_ok=True)
    report = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for width, height in [(1440, 1000), (390, 844)]:
                page = browser.new_page(viewport={'width': width, 'height': height})
                page.goto(url, wait_until='networkidle')
                page.wait_for_function("document.querySelector('.hero-visual img').src.endsWith('/thiamine-deficiency-2-beriberi-diagnosis/infographic.png')")
                for img in page.locator('img').all():
                    img.scroll_into_view_if_needed()
                    img.evaluate('(img) => img.decode()')
                images = page.locator('img').evaluate_all('xs => xs.map(x => ({src:x.src, width:x.naturalWidth, complete:x.complete}))')
                assert all(x['width'] > 0 and x['complete'] for x in images), images
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.evaluate('scrollTo(0,0)')
                page.screenshot(path=str(evidence / f'preview-{width}.png'), full_page=True)
                report.append({'width':width, 'images':images, 'overflow':False})
                page.close()
            page = browser.new_page()
            page.route('**/infographics/manifest.json', lambda r: r.fulfill(json={'items':[{'slug':'missing-test','title':'Missing','date':'2099-01-01'}]}))
            page.route('**/missing-test/**', lambda r:r.fulfill(status=404))
            page.goto(url, wait_until='networkidle')
            assert 'essential-tremor-treatment-2026/thumb.png' in page.locator('.hero-visual img').get_attribute('src')
            assert page.locator('#visual-preview img').count() == 3
            report.append({'both_images_missing':'existing verified hero and tiles preserved'})
            browser.close()
        (evidence / 'qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PASS: desktop/mobile all images decoded, no overflow, both-missing fallback preserved')
    finally:
        server.shutdown()
        server.server_close()

if __name__ == '__main__':
    main()
