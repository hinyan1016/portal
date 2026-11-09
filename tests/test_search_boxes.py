"""検索の主役は冒頭の窓で、ライブラリー側は「一覧を絞り込む」補助の欄であることを、正本と生成物の両方で検証する。"""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', ['src/index.html', 'index.html'])
def test_hero_search_stays_the_main_entry(name):
    html = (ROOT / name).read_text(encoding='utf-8')
    assert html.count('id="hero-search"') == 1 and html.count('id="hero-q"') == 1
    hero = html[html.index('id="hero-search"'):html.index('</form>', html.index('id="hero-search"'))]
    assert '>探す</button>' in hero


@pytest.mark.parametrize('name', ['src/index.html', 'index.html'])
def test_library_search_reads_as_a_filter_and_keeps_its_hooks(name):
    html = (ROOT / name).read_text(encoding='utf-8')
    # app.js とブラウザ検査が使う目印は変えない。
    for hook in ('id="search-form"', 'id="site-search"', 'id="search-submit"'):
        assert html.count(hook) == 1, hook
    form = html[html.index('id="search-form"'):html.index('</form>', html.index('id="search-form"'))]
    assert 'aria-controls="content-grid"' in form
    assert '<kbd aria-hidden="true">/</kbd>' in form
    assert '<button type="submit" id="search-submit">絞り込む</button>' in form
    assert re.search(r'<label class="sr-only" for="site-search">[^<]*絞り込[^<]*</label>', form)
    placeholder = re.search(r'id="site-search"[^>]*placeholder="([^"]*)"', form)
    assert placeholder and '絞り込' in placeholder.group(1)
    # 幅320でも切れない長さ（「キーワードで一覧を絞り込む」は末尾が欠けた）。
    assert len(placeholder.group(1)) <= 10
    # 緑の主ボタン「検索」を冒頭と二重に並べない。
    assert '>検索' not in form and '横断検索' not in html


def test_library_search_button_is_outlined_not_primary():
    css = (ROOT / 'styles.css').read_text(encoding='utf-8')
    rule = re.search(r'#search-form button\{([^}]*)\}', css)
    assert rule
    body = rule.group(1)
    assert 'background:transparent' in body and 'border:1px solid var(--line)' in body
    # タップ領域は44px以上を保つ。
    assert 'min-height:44px' in body
    assert '#search-form input{height:44px}' in css
