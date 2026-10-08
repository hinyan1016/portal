"""SNS共有画像（OGP）とアイコンを assets/ に書き出す。デザインを変えたときだけ手元で実行する。

- assets/og-image.png        1200×630（og:image・twitter:card）
- assets/apple-touch-icon.png 180×180（iPhoneのホーム画面）
- assets/icon-512.png         512×512（構造化データのロゴ）

使い方: python scripts/build_brand_images.py （Playwright と Chromium が必要）
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FONTS = '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@500;700&family=Noto+Serif+JP:wght@500&display=block" rel="stylesheet">'
MARK = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="{rx}" fill="#173e3b"/><path d="M24 10v28M10 24h28" stroke="#f5f4ed" stroke-width="3.5"/><circle cx="34" cy="14" r="4" fill="#b8cf8e"/></svg>'

OG = """<!doctype html><html lang="ja"><head><meta charset="utf-8">{fonts}<style>
*{{box-sizing:border-box;margin:0}}
body{{width:1200px;height:630px;display:grid;grid-template-columns:1fr 330px;background:#fcfcf9;color:#203833;font-family:'Noto Sans JP',sans-serif}}
main{{padding:62px 0 56px 76px;display:flex;flex-direction:column}}
.brand{{display:flex;align-items:center;gap:18px;font-size:34px;font-weight:700;letter-spacing:.04em}}
.brand svg{{width:64px;height:64px}}
.brand small{{display:block;font-size:13px;font-weight:500;letter-spacing:.26em;margin-top:4px;color:#62716a}}
h1{{font-family:'Noto Serif JP',serif;font-weight:500;font-size:68px;line-height:1.5;letter-spacing:.03em;margin-top:44px}}
h1 em{{font-style:normal;color:#205d51;text-decoration:underline;text-decoration-color:#c8d9b5;text-decoration-thickness:10px;text-underline-offset:12px;text-decoration-skip-ink:none}}
p{{margin-top:auto;font-size:25px;font-weight:500;color:#41534c}}
p span{{display:block;margin-top:10px;font-size:19px;letter-spacing:.12em;color:#205d51}}
aside{{background:#173e3b;position:relative;overflow:hidden}}
aside i{{position:absolute;border:1.5px solid #78998966;border-radius:50%}}
aside b{{position:absolute;width:46px;height:46px;border-radius:50%;background:#b8cf8e;right:72px;top:118px}}
</style></head><body><main>
<div class="brand">{mark}<span>医知創造ラボ<small>ICHISOUZO LAB</small></span></div>
<h1>知ることが、<br><em>安心と力</em>になる。</h1>
<p>脳神経内科専門医が編集する、医療と健康のライブラリー<span>記事 ・ 図解 ・ 動画 ・ スライド ・ ツール</span></p>
</main><aside><i style="width:420px;height:420px;left:-40px;top:150px"></i><i style="width:300px;height:300px;left:60px;top:40px"></i><i style="width:200px;height:200px;left:150px;top:330px"></i><b></b></aside></body></html>"""


def main():
    assets = ROOT / 'assets'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1200, 'height': 630})
        page.set_content(OG.format(fonts=FONTS, mark=MARK.format(rx=14)), wait_until='networkidle')
        page.evaluate('document.fonts.ready')
        page.screenshot(path=str(assets / 'og-image.png'))
        for name, size, rx, transparent in [('apple-touch-icon.png', 180, 0, False), ('icon-512.png', 512, 14, True)]:
            page = browser.new_page(viewport={'width': size, 'height': size})
            page.set_content(f'<html><body style="margin:0;background:transparent">{MARK.format(rx=rx).replace("<svg ", f"<svg width={size} height={size} ")}</body></html>')
            page.screenshot(path=str(assets / name), omit_background=transparent)
        browser.close()
    for name in ['og-image.png', 'apple-touch-icon.png', 'icon-512.png']:
        print(name, (assets / name).stat().st_size // 1024, 'KB')


if __name__ == '__main__':
    main()
