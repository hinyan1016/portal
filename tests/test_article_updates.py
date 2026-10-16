import pytest
from article_updates import render, validate


def item(**kw):
    row = dict(id='verified-example', date='2026-10-12', title='記事 <確認>', summary='図解 & 説明を追加。', url='https://blog.ichisouzo-lab.com/entry/2026/10/08/121828', public_verified=True, evidence='テスト専用。実データではない。')
    return dict(row, **kw)


def test_empty_state_and_escaped_content():
    assert '現在、掲載する更新情報はありません' in render([])
    s = render([item()])
    assert '&lt;確認&gt;' in s and '&amp;' in s
    assert '<time datetime="2026-10-12">' in s


@pytest.mark.parametrize('kw', [dict(public_verified=False), dict(evidence=''), dict(date='2026-02-30'), dict(date='2099-01-01'), dict(url='javascript:alert(1)'), dict(url='https://blog.ichisouzo-lab.com.evil.test/entry/a')])
def test_unverified_future_and_unsafe_records_fail_closed(kw):
    with pytest.raises(ValueError):
        validate([item(**kw)])


def test_sorting_duplicate_and_archive():
    rows = [item(id=str(i), date='2026-10-0'+str(i+1)) for i in range(7)]
    s = render(rows)
    assert s.index('2026-10-07') < s.index('2026-10-01')
    assert '<details>' in s and s.count('<li>') == 7
    with pytest.raises(ValueError):
        validate([item(), item()])
