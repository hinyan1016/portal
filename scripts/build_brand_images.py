"""SNS共有画像（OGP）とアイコンを書き出す。デザインを変えたときだけ手元で実行する。

- assets/og-image.png        1200×630（og:image・twitter:card）
- assets/apple-touch-icon.png 180×180（iPhoneのホーム画面）
- assets/icon-512.png         512×512（構造化データのロゴ）
- --sister tools=<パス> / check=<パス> で、姉妹サイト（診断支援ツール・症状セルフチェック）の共有画像も書き出す。

使い方: python scripts/build_brand_images.py [--sister tools=../medical-ddx-tools/assets/og-tools.png]
（Playwright と Chromium が必要）
"""
import argparse
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

# 姉妹サイトは、それぞれのサイトの配色（紺・青）で、見出しと対象読者を示す。文言は各サイトの一覧ページの既存の表記。
SISTER = {
    'tools': {'panel': '#15324E', 'accent': '#1B3A5C', 'title': '臨床鑑別診断ツール集',
              'lead': '臨床所見・検査所見から系統的に<br>鑑別診断を行うインタラクティブツール',
              'tag': '医療従事者・研修医向け ・ tools.ichisouzo-lab.com'},
    'check': {'panel': '#2C5AA0', 'accent': '#2C5AA0', 'title': 'その症状、大丈夫？',
              'lead': '脳神経内科医監修<br>セルフチェックツール',
              'tag': '一般の方・ご家族向け ・ 診断ではありません'},
}
SISTER_OG = """<!doctype html><html lang="ja"><head><meta charset="utf-8">{fonts}<style>
*{{box-sizing:border-box;margin:0}}
body{{width:1200px;height:630px;display:grid;grid-template-columns:1fr 330px;background:#f6f8fb;color:#1b2b3a;font-family:'Noto Sans JP',sans-serif}}
main{{padding:62px 0 56px 76px;display:flex;flex-direction:column}}
.brand{{display:flex;align-items:center;gap:18px;font-size:34px;font-weight:700;letter-spacing:.04em}}
.brand svg{{width:64px;height:64px}}
.brand small{{display:block;font-size:13px;font-weight:500;letter-spacing:.26em;margin-top:4px;color:#5d6b78}}
h1{{font-weight:700;font-size:66px;line-height:1.35;letter-spacing:.02em;margin-top:52px;color:{accent}}}
.lead{{margin-top:22px;font-size:30px;font-weight:500;line-height:1.6;color:#33475b}}
.tag{{margin-top:auto;font-size:21px;font-weight:500;letter-spacing:.06em;color:{accent}}}
aside{{background:{panel};position:relative;overflow:hidden}}
aside i{{position:absolute;border:1.5px solid #ffffff40;border-radius:50%}}
aside b{{position:absolute;width:46px;height:46px;border-radius:50%;background:#b8cf8e;right:72px;top:118px}}
</style></head><body><main>
<div class="brand">{mark}<span>医知創造ラボ<small>ICHISOUZO LAB</small></span></div>
<h1>{title}</h1>
<div class="lead">{lead}</div>
<div class="tag">{tag}</div>
</main><aside><i style="width:420px;height:420px;left:-40px;top:150px"></i><i style="width:300px;height:300px;left:60px;top:40px"></i><i style="width:200px;height:200px;left:150px;top:330px"></i><b></b></aside></body></html>"""


def shoot(browser, html, path, width=1200, height=630, transparent=False):
    page = browser.new_page(viewport={'width': width, 'height': height})
    page.set_content(html, wait_until='networkidle')
    page.evaluate('document.fonts.ready')
    page.screenshot(path=str(path), omit_background=transparent)
    page.close()
    print(Path(path).name, Path(path).stat().st_size // 1024, 'KB')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sister', action='append', default=[], metavar='SITE=PATH', help='tools=… または check=… の出力先')
    parser.add_argument('--skip-portal', action='store_true', help='ポータル自身の画像は書き出さない')
    args = parser.parse_args()
    assets = ROOT / 'assets'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        if not args.skip_portal:
            shoot(browser, OG.format(fonts=FONTS, mark=MARK.format(rx=14)), assets / 'og-image.png')
            for name, size, rx, transparent in [('apple-touch-icon.png', 180, 0, False), ('icon-512.png', 512, 14, True)]:
                mark = MARK.format(rx=rx).replace('<svg ', f'<svg width={size} height={size} ')
                shoot(browser, f'<html><body style="margin:0;background:transparent">{mark}</body></html>', assets / name, size, size, transparent)
        for item in args.sister:
            site, _, out = item.partition('=')
            shoot(browser, SISTER_OG.format(fonts=FONTS, mark=MARK.format(rx=14), **SISTER[site]), Path(out))
        browser.close()


if __name__ == '__main__':
    main()
