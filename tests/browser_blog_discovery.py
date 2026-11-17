"""公開トップ上で、既存版・配信前差し替え・公開後の検索と更新タブを照合する。"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BLOG = 'https://blog.ichisouzo-lab.com/'
# 検索文ごとに、上位3件で見つけたい資料のURLまたは題名を事前指定する。
GENERAL = [
    ('頭を打ったあとに気をつけること', '/2026/05/06/204047'),
    ('手が震える原因を知りたい', '振戦の見分け方'),
    ('夜眠れないときはどうすればいい', '眠れないのは脳のせい'),
    ('物が二つに見える', '複視'),
    ('飲み込みにくいときの食事', '嚥下障害の食事'),
    ('足がむくんだ', '浮腫|むくみ'),
    ('目が回るのはなぜ', 'めまい'),
    ('手足がしびれるとき何科に行く', '手足がしびれる'),
    ('採血のあとに手がしびれる', '採血後の痛みやしびれ'),
    ('便が出ないので生活でできることを知りたい', '便秘の生活'),
    ('頭が痛い', '頭痛'),
    ('胸が痛いとき', '胸痛|胸が痛'),
    ('お腹が痛いとき', '腹痛|お腹が痛'),
    ('息が苦しいとき', '呼吸困難|息が苦しい'),
    ('手のふるえに薬が効かない', '手のふるえ、薬が効かなかったら'),
]
PROFESSIONAL = [
    ('ワルファリンの量を調整したい', 'warfarin_dose_adjuster'),
    ('救急で使う薬を復習したい', '/2025/05/13/064051'),
    ('ASPECTSを計算したい', 'aspects_calculator'),
    ('神経伝導検査の所見を書きたい', 'ncs_report_writer'),
    ('脳波の所見を作成したい', 'eeg_report_writer'),
    ('患者さんの紹介状を作成したい', 'referral_helper'),
    ('症状詳記を作成したい', 'shojo_shoki_helper'),
    ('IVIGの投与量を計算したい', 'ivig_calculator'),
    ('必要なエネルギーと水分量を計算したい', 'calorie_protein_calculator'),
    ('てんかん重積の薬剤投与量を計算したい', 'status_epilepticus_initial_calculator'),
    ('脳梗塞の病状説明をカルテに記録したい', 'stroke_ic_note'),
    ('周術期の抗血栓薬の返書を作りたい', 'periop_antithrombotic_consult'),
    ('神経学的診察所見の記載を補助するツール', 'neuro_exam_helper'),
    ('脳出血の抗発作薬のスライドを見たい', 'hemorrhagic-stroke-seizure-prophylaxis'),
    ('低ナトリウム血症の鑑別ツールを探したい', 'hyponatremia.html'),
]


def mount(page):
    staged = ROOT / '_site'
    def serve(route):
        asset = Path(urlsplit(route.request.url).path).name
        mime = {'.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json'}
        route.fulfill(body=(staged / asset).read_bytes(), content_type=mime[Path(asset).suffix],
                      headers={'Access-Control-Allow-Origin': '*'})
    for name in ('blog-home-stage5.css', 'blog-home-stage5.js', 'blog-topic-search.js',
                 'blog-topic-index.json', 'blog-home-feed.json'):
        page.route('https://ichisouzo-lab.com/' + name + '*', serve)


def run(mode, out):
    baseline = mode == 'before'
    result = {'mode': mode, 'queries': {}, 'widths': {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome')
        for width in (390, 1280):
            page = browser.new_page(viewport={'width': width, 'height': 844}, locale='ja-JP',
                                    has_touch=width == 390, is_mobile=width == 390)
            if mode == 'preview':
                mount(page)
            if not baseline:
                errors = []
                page.on('pageerror', lambda exc: errors.append(str(exc)))
            page.goto(BLOG, wait_until='domcontentloaded')
            query = page.locator('#ich-search-query')
            page.locator('#ich-search-suggest' if baseline else '#ich-topic-results').wait_for(state='attached')
            query.focus()
            if baseline:
                page.wait_for_function("!!performance.getEntriesByType('resource').find(r=>r.name.includes('search-index.json'))")
            else:
                page.wait_for_function("!!performance.getEntriesByType('resource').find(r=>r.name.includes('blog-topic-index.json'))")
            for phrase, target in (GENERAL + PROFESSIONAL if width == 390 else [GENERAL[0], *PROFESSIONAL[:2]]):
                query.fill(phrase)
                if baseline:
                    page.wait_for_function("!document.querySelector('#ich-search-suggest').innerText.includes('読み込んで')")
                    groups = page.locator('#ich-search-suggest .ich-suggest-item')
                else:
                    page.wait_for_function("!document.querySelector('.ich-topic-status').innerText.includes('読み込んで')")
                    groups = page.locator('.ich-topic-group')
                data = groups.evaluate_all("""els=>els.slice(0,3).map(el=>({
                  title:el.querySelector('h3')?.textContent || el.textContent,
                  urls:el.matches('a')?[el.href]:[...el.querySelectorAll('a')].map(a=>a.href)
                }))""")
                position = next((i+1 for i,x in enumerate(data) if re.search(target,x['title']+' '+' '.join(x['urls']))), None)
                result['queries'][phrase] = {'target':target, 'position':position, 'first3':data}
                if not baseline and phrase in (GENERAL[0][0], PROFESSIONAL[0][0], PROFESSIONAL[1][0]):
                    assert position == 1, (phrase,data)
                    if phrase == GENERAL[0][0]:
                        assert len(data[0]['urls']) >= 3 and any('youtube.com' in u for u in data[0]['urls'])
                    if phrase == PROFESSIONAL[0][0]:
                        assert 'warfarin_dose_adjuster' in data[0]['urls'][0] and any('/entry/' in u for u in data[0]['urls'])
            if not baseline:
                query.fill('ワルファリンの量を調整したい')
                query.press('Enter')
                assert page.url == BLOG and page.locator('.ich-topic-link').first.is_visible()
                page.locator('form.ich-search button[type=submit]').click()
                assert page.url == BLOG
                query.focus()
                query.press('ArrowDown')
                assert page.evaluate("document.activeElement.classList.contains('ich-topic-link')")
                page.keyboard.press('Escape')
                assert page.locator('#ich-topic-results').is_hidden()
                query.fill('zxq971xyz')
                assert '見つかりません' in page.locator('.ich-topic-status').inner_text()
                assert page.locator('.ich-topic-full').get_attribute('href').endswith('q=zxq971xyz')
                query.press('Escape')
                updated = page.get_by_role('tab', name='最近更新した記事')
                updated.scroll_into_view_if_needed()
                top = updated.evaluate('el=>Math.round(el.getBoundingClientRect().top+scrollY)')
                if width == 390:
                    updated.tap()
                else:
                    updated.click()
                cards = page.locator('.ich-revision-card')
                cards.first.wait_for(state='visible', timeout=5000)
                assert cards.count() >= 3 and cards.first.locator('p').inner_text()
                urls = cards.locator('h3 a').evaluate_all('els=>els.map(a=>a.href)')
                assert page.locator('.pager-next a').first.get_attribute('href').endswith('article-updates.html')
                assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
                if out:
                    page.screenshot(path=out / f'{mode}-{width}-updates.png')
                updated.press('ArrowLeft')
                assert page.locator('#ich-filter-tab-all').get_attribute('aria-selected') == 'true'
                assert page.locator('#main .archive-entry').count() > 0
                page.locator('#ich-filter-tab-general').click()
                assert page.locator('#main .archive-entry').count() > 0
                query.fill(GENERAL[0][0])
                if out:
                    page.screenshot(path=out / f'{mode}-{width}-search.png')
                result['widths'][width] = {'update_tab_y':top, 'updates':urls, 'page_errors':errors}
                assert not errors, errors
            page.close()
        if not baseline:
            page = browser.new_page(viewport={'width':320,'height':700})
            if mode == 'preview':
                mount(page)
            page.goto(BLOG + '#recent-updates', wait_until='domcontentloaded')
            page.locator('.ich-revision-card h3 a').first.wait_for()
            assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
            page.locator('#ich-search-query').focus()
            page.get_by_role('button',name=GENERAL[0][0],exact=True).click()
            page.locator('.ich-topic-group').first.wait_for()
            assert page.locator('.ich-topic-link').first.get_attribute('href').endswith('2026/05/06/204047')
            for path in ('?page=2','entry/2026/05/06/204047'):
                page.goto(BLOG + path, wait_until='domcontentloaded')
                page.locator('#ich-search-suggest').wait_for(state='attached')
                assert page.locator('#ich-filter-tab-updated').count() == 0
            page.goto(BLOG + '?utm_source=qa', wait_until='domcontentloaded')
            page.locator('#ich-topic-results').wait_for(state='attached')
            page.get_by_role('tab',name='最近更新した記事').wait_for()
            page.close()
        browser.close()
    for cohort in (GENERAL, PROFESSIONAL):
        print(sum(result['queries'][q]['position'] is not None for q,_ in cohort), '/', len(cohort))
    if out:
        (out / f'{mode}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['before','preview','live'])
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
    run(args.mode, args.out)
