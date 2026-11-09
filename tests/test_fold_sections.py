"""スマホで下の3節を開閉するボタンが、正本と生成物の両方に正しい形で入っていることを検証する。"""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUTTON = re.compile(r'<button class="fold-toggle" type="button" aria-expanded="false" data-fold="([a-z]+)">(.*?)</button>')


@pytest.mark.parametrize('name', ['src/index.html', 'index.html'])
def test_fold_buttons_point_at_their_sections_and_say_how_to_use(name):
    html = (ROOT / name).read_text(encoding='utf-8')
    found = BUTTON.findall(html)
    assert [section for section, _ in found] == ['offline', 'columns', 'about']
    assert html.count('class="fold-toggle"') == 3
    for section, inner in found:
        assert 'id="' + section + '"' in html
        # ボタンは自分の節の中にある（節の開始より後・次の節より前）。
        start = html.index('id="' + section + '"')
        end = html.find('<section', start + 1)
        position = html.index('data-fold="' + section + '"')
        assert start < position and (end == -1 or position < end)
        assert '<small>タップで開閉</small>' in inner
        assert 'class="fold-closed"' in inner and 'class="fold-opened"' in inner


def test_fold_is_hidden_by_default_and_only_folds_on_narrow_screens():
    css = (ROOT / 'styles.css').read_text(encoding='utf-8')
    assert '.fold-toggle{display:none}' in css
    media = css.index('@media screen and (max-width:680px){', css.index('.fold-toggle{display:none}'))
    # 畳む指定は、JavaScriptが付ける fold-on とスマホ幅の両方がそろったときだけ効く。
    hiding = [m.start() for m in re.finditer(r'\.fold-on:not\(\.fold-open\)', css)]
    assert hiding and min(hiding) > media
    assert 'fold-on' not in (ROOT / 'src/index.html').read_text(encoding='utf-8')


def test_fold_script_is_started_and_keeps_old_safari_syntax():
    js = (ROOT / 'app.js').read_text(encoding='utf-8')
    assert 'function initFold()' in js and 'initFold();' in js
    body = js[js.index('function initFold()'):js.index('initHomeFeed(); initFold();')]
    assert not re.search(r'\b(const|let)\s|=>', body)
    assert 'console.log' not in js
