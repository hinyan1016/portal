from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
import sys

import pytest

from home_sections import MARKERS, WEEKLY_PICKS_MARKER, apply, render_weekly_picks
from tests.test_home_feed import feed, CONFIG
from weekly_picks import (KINDS, clean_item, safe_image, select_weekly, update_history,
                          validate_selection, valid_url, week_start)


TODAY = date(2026, 11, 2)


def catalog():
    rows = []
    for i in range(5):
        article = f'https://blog.ichisouzo-lab.com/entry/2026/09/{i + 1:02d}/000000'
        rows += [dict(t=f'記事{i}', u=article, k='記事', a='general', d='2026-09-01'),
                 dict(t=f'図解{i}', u=f'https://tools.ichisouzo-lab.com/infographics/example-{i}/',
                      k='図解', a='both', group=article),
                 dict(t=f'ツール{i}', u=f'https://tools.ichisouzo-lab.com/calculator_{i}.html',
                      k='ツール', a='professional')]
    return rows


def choose(rows=None, previous=None, history=None, today=TODAY, available=lambda _url: True):
    return select_weekly(catalog() if rows is None else rows, previous, history or [], today, available)


def test_jst_monday_boundary_and_year_boundary():
    assert week_start(datetime(2026, 11, 1, 14, 59, tzinfo=timezone.utc)) == '2026-10-26'
    assert week_start(datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc)) == '2026-11-02'
    assert week_start(date(2027, 1, 3)) == '2026-12-28'
    assert week_start(date(2027, 1, 4)) == '2027-01-04'
    with pytest.raises(ValueError):
        week_start(datetime(2026, 11, 2))


def test_same_week_stays_fixed_after_catalog_updates_and_next_week_rotates():
    rows = catalog()
    before = deepcopy(rows)
    first = choose(rows)
    history = update_history([], first)
    shuffled = list(reversed(rows)) + [dict(t='新しい記事', u='https://blog.ichisouzo-lab.com/entry/2026/11/03/000000',
                                         k='記事', a='general', d='2026-11-03')]
    def unexpected_check(_url):
        raise AssertionError('同じ週は再選定のリンク確認をしない')
    same = choose(shuffled, first, history, TODAY + timedelta(days=3), unexpected_check)
    assert [x['u'] for x in same['items']] == [x['u'] for x in first['items']]
    following = choose(rows, first, history, TODAY + timedelta(days=7))
    assert following['week'] == '2026-11-09'
    assert tuple(x['k'] for x in following['items']) == KINDS
    assert {x['u'] for x in first['items']}.isdisjoint(x['u'] for x in following['items'])
    assert len({x['group'] for x in following['items']}) == 3
    assert rows == before


def test_removed_item_is_replaced_without_rotating_the_other_two():
    previous = choose()
    removed = previous['items'][1]['u']
    rows = [row for row in catalog() if row['u'] != removed]
    current = choose(rows, previous, update_history([], previous))
    assert current['items'][0]['u'] == previous['items'][0]['u']
    assert current['items'][2]['u'] == previous['items'][2]['u']
    assert current['items'][1]['u'] != removed


def test_small_catalog_avoids_consecutive_repeats_even_after_every_item_was_used():
    previous, history = None, []
    for i in range(12):
        current = choose(previous=previous, history=history, today=TODAY + timedelta(weeks=i))
        if previous:
            assert {x['u'] for x in previous['items']}.isdisjoint(x['u'] for x in current['items'])
        history = update_history(history, current)
        previous = current


def test_unique_topics_backtrack_and_broken_links_are_skipped():
    rows = catalog()
    figure = next(row for row in rows if row['k'] == '図解')
    rows = [row for row in rows if row['k'] != '図解'] + [figure]
    blocked = 'https://tools.ichisouzo-lab.com/calculator_0.html'
    picked = choose(rows, available=lambda url: url != blocked)
    assert len({x['group'] for x in picked['items']}) == 3
    assert all(x['u'] != blocked for x in picked['items'])
    assert picked['items'][0]['u'] != figure['group']
    with pytest.raises(ValueError):
        choose(rows, available=lambda _url: False)


def test_unknown_reader_future_and_untrusted_destinations_are_not_candidates():
    for kind, url in [('記事', 'https://blog.ichisouzo-lab.com.evil.test/entry/2026/09/01/000000'),
                      ('図解', 'javascript:alert(1)'), ('ツール', 'https://tools.ichisouzo-lab.com/private/index.html')]:
        assert clean_item(dict(t='候補', u=url, k=kind, a='general')) is None
    assert not valid_url('https://[', '記事')
    assert clean_item(dict(catalog()[0], a='unspecified')) is None
    assert clean_item(dict(catalog()[0], d='2026-12-01'), TODAY) is None
    assert safe_image('thumbs/../../secrets.png') == ''
    assert safe_image('https://evil.test/a.webp') == ''
    assert safe_image('thumbs/example.webp') == 'thumbs/example.webp'
    with pytest.raises(ValueError):
        choose([x for x in catalog() if x['k'] != 'ツール'])


def test_history_is_bounded_and_same_week_does_not_add_duplicate_records():
    selected = choose()
    history = []
    for i in range(12):
        selected = dict(selected, week=(TODAY + timedelta(weeks=i)).isoformat())
        history = update_history(history, selected)
    assert len(history) == 8
    assert len({x['week'] for x in history}) == 8
    assert update_history(history, selected) == history


def test_renderer_escapes_titles_and_handles_image_free_cards():
    selection = choose()
    selection['items'][0]['t'] = '見出し <script> & "引用"'
    html = render_weekly_picks(selection)
    assert '&lt;script&gt;' in html and '&amp;' in html and '&quot;引用&quot;' in html
    assert html.count('data-pick-kind=') == 3
    assert html.count('home-pick-placeholder') == 3
    assert 'data-pick-week="2026-11-02"' in html
    data = dict(feed(), weekly_picks=selection)
    assert WEEKLY_PICKS_MARKER not in apply('\n'.join(MARKERS + (WEEKLY_PICKS_MARKER,)), data)
    with pytest.raises(ValueError):
        validate_selection(dict(selection, items=selection['items'][:2]))
    with pytest.raises(ValueError):
        apply('\n'.join(MARKERS + (WEEKLY_PICKS_MARKER,) * 2), data)


def test_refresh_main_saves_selection_and_keeps_previous_on_selection_failure(tmp_path, monkeypatch):
    import scripts.refresh_home as refresh
    for name, filename in [('FEED_PATH', 'feed.json'), ('STATE_PATH', 'state.json'),
                           ('CONFIG_PATH', 'config.json'), ('CATALOG_PATH', 'catalog.json'),
                           ('UPDATES_PATH', 'updates.json')]:
        monkeypatch.setattr(refresh, name, tmp_path / filename)
    refresh.write_json(refresh.FEED_PATH, feed())
    refresh.write_json(refresh.CONFIG_PATH, CONFIG)
    refresh.write_json(refresh.CATALOG_PATH, catalog())
    monkeypatch.setattr(refresh, 'today_jst', lambda: TODAY)
    monkeypatch.setattr(refresh, 'public_link_available', lambda _url: True)
    def unavailable_feed(*_args):
        raise OSError('このテストでは外部取得を行わない')
    monkeypatch.setattr(refresh, 'fetch', unavailable_feed)
    monkeypatch.setattr(sys, 'argv', ['refresh_home.py'])
    refresh.main()
    first = refresh.FEED_PATH.read_bytes()
    payload = json.loads(first)
    assert payload['weekly_picks']['week'] == '2026-11-02'
    assert len(json.loads(refresh.STATE_PATH.read_text(encoding='utf-8'))['weekly_picks_history']) == 1
    refresh.write_json(refresh.CATALOG_PATH, [])
    refresh.main()
    assert refresh.FEED_PATH.read_bytes() == first
