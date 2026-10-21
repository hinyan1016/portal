"""トップの自動更新枠（医学の新着・最近更新した記事・ツールの近道・オフライン版）を検証する。"""
from datetime import date
import json

import pytest

from home_sections import MARKERS, apply, render_medical_news, render_tool_shortcuts
from scripts.refresh_home import (channel_video_ids, general_tools, lead_summary, medical_news, merge_updates,
                                  newest_first, offline_release, pro_tools, revision_notice, scan_revisions,
                                  split_title, tool_label)

CONFIG = {'medical_news_count': 2, 'medical_categories': ['脳神経内科', '医学情報'], 'new_tool_count': 1,
          'pro_tool_staples': [{'url': 'https://tools.ichisouzo-lab.com/headache.html', 'label': '頭痛鑑別'}],
          'new_handout_count': 1, 'handout_audience_words': ['患者', '一般'],
          'revision_fetch_limit': 2, 'revision_lookback_days': 30, 'revision_notice_window_days': 7}
REL = 'https://github.com/hinyan1016/medical-ddx-tools/releases/'


def feed():
    return {'medical_news': [{'title': '記事 <A>', 'url': 'https://blog.ichisouzo-lab.com/entry/2026/10/21/084039',
                              'date': '2026-10-21', 'audience_label': '医師向け', 'summary': '整理 & 解説。', 'video': 'Qas2OdVQczU'}],
            'pro_tools': [{'url': 'https://tools.ichisouzo-lab.com/headache.html', 'label': '頭痛鑑別'}],
            'general_tools': [{'url': 'https://tools.ichisouzo-lab.com/handouts/x/', 'label': '資料'}],
            'offline': {'version': 'v1.4', 'date': '2026-10-19', 'release_url': REL + 'tag/offline-v1.4',
                        'full': {'url': REL + 'download/offline-v1.4/a.zip', 'size_mb': 100.4, 'text': '332件'},
                        'lite': {'url': REL + 'download/offline-v1.4/b.zip', 'size_mb': 11.8, 'text': '162件'}}}


# ---- 描画 ----------------------------------------------------------------------

def test_render_escapes_and_links_video_only_when_given():
    html = render_medical_news(feed()['medical_news'])
    assert '記事 &lt;A&gt;' in html and '整理 &amp; 解説。' in html and '2026/10/21</time> 公開 · 医師向け' in html
    assert 'youtube.com/watch?v=Qas2OdVQczU' in html
    no_video = dict(feed()['medical_news'][0], video='')
    assert 'youtube' not in render_medical_news([no_video])


@pytest.mark.parametrize('kw', [dict(url='https://evil.example/entry/1'), dict(url='javascript:alert(1)'),
                                dict(video='"><script>'), dict(date='2026-02-30'), dict(summary='')])
def test_news_rejects_unsafe_or_broken_values(kw):
    with pytest.raises(ValueError):
        render_medical_news([dict(feed()['medical_news'][0], **kw)])


def test_tools_and_offline_reject_foreign_hosts():
    with pytest.raises(ValueError):
        render_tool_shortcuts([{'url': 'https://tools.ichisouzo-lab.com.evil.test/a.html', 'label': 'x'}])
    bad = feed()
    bad['offline']['full']['url'] = 'https://example.com/a.zip'
    with pytest.raises(ValueError):
        apply('\n'.join(MARKERS), bad)


def test_apply_fills_every_marker_once_and_keeps_old_templates():
    out = apply('\n'.join(MARKERS), feed())
    assert '<!--' not in out
    assert '最新版 v1.4（2026年10月19日）' in out and 'ZIP・100.4 MB' in out and 'ZIP・11.8 MB' in out
    assert apply('<p>旧テンプレート</p>', feed()) == '<p>旧テンプレート</p>'
    with pytest.raises(ValueError):
        apply('\n'.join(MARKERS + MARKERS[:1]), feed())


# ---- 医学の新着 ----------------------------------------------------------------

def rss_item(title, path, day, cats, desc):
    cats = ''.join(f'<category>{c}</category>' for c in cats)
    return (f'<item><title>{title}</title><link>https://blog.ichisouzo-lab.com/entry/{path}</link>'
            f'<pubDate>{day}</pubDate>{cats}<description><![CDATA[{desc}]]></description></item>')


def test_medical_news_filters_categories_and_links_only_public_videos():
    lead = '<p class="lead-text">導入の文です。この記事では、検査の考え方を整理します。</p><iframe src="https://www.youtube-nocookie.com/embed/Jyu9wJyQjgI"></iframe>'
    xml = '<rss><channel>' + ''.join([
        rss_item('新しい医学記事【医師向け】', '2026/10/21/090000', 'Wed, 21 Oct 2026 09:00:00 +0900', ['脳神経内科'], lead),
        rss_item('生活の話', '2026/10/21/100000', 'Wed, 21 Oct 2026 10:00:00 +0900', ['生活'], lead),
        rss_item('限定動画の記事', '2026/10/20/090000', 'Tue, 20 Oct 2026 09:00:00 +0900', ['医学情報'],
                 '<p>本文です。</p><iframe src="https://www.youtube.com/embed/-ZNOUEYXVNI"></iframe>'),
        rss_item('古い記事', '2026/10/19/090000', 'Mon, 19 Oct 2026 09:00:00 +0900', ['医学情報'], '<p>古い。</p>'),
    ]) + '</channel></rss>'
    rows = medical_news(xml, CONFIG, {'Jyu9wJyQjgI'})
    assert [r['title'] for r in rows] == ['新しい医学記事', '限定動画の記事']
    assert rows[0]['audience_label'] == '医師向け' and rows[0]['summary'] == 'この記事では、検査の考え方を整理します。'
    assert rows[0]['video'] == 'Jyu9wJyQjgI' and rows[1]['video'] == ''


def test_title_and_summary_helpers():
    assert split_title('A｜B【一般向け】') == ('A｜B', '一般向け')
    assert split_title('A【完全解説】') == ('A', '')
    assert lead_summary('<p>最初の文。次の文。</p>') == '最初の文。'
    long = lead_summary('<p>' + 'あ' * 60 + '、' + 'い' * 60 + '。</p>')
    assert long.endswith('…') and len(long) <= 90
    assert channel_video_ids('<yt:videoId>Qas2OdVQczU</yt:videoId>') == ['Qas2OdVQczU']


# ---- ツールの近道 --------------------------------------------------------------

def test_new_tools_first_then_staples():
    html = ('<a class="tool-card" href="new.html"><div class="tool-name">新しい計算ツール（試用）</div></a>'
            '<a class="tool-card" href="old.html"><div class="tool-name">古いツール</div></a>'
            '<a class="tool-card" href="headache.html"><div class="tool-name">頭痛</div></a>')
    state = {'tools_first_seen': {'https://tools.ichisouzo-lab.com/old.html': '2026-01-01'}}
    rows = pro_tools(html, CONFIG, state, '2026-10-21')
    assert rows == [{'url': 'https://tools.ichisouzo-lab.com/new.html', 'label': '新しい計算'},
                    {'url': 'https://tools.ichisouzo-lab.com/headache.html', 'label': '頭痛鑑別'}]
    assert state['tools_first_seen']['https://tools.ichisouzo-lab.com/new.html'] == '2026-10-21'
    assert tool_label('日常生活自立度 判定支援ツール') == '日常生活自立度 判定支援'


def test_newest_first_keeps_list_order_for_same_day():
    seen = {'a': '2026-10-01', 'b': '2026-10-01', 'c': '2026-10-05'}
    assert newest_first(['a', 'b', 'c'], seen, '2026-10-21') == ['c', 'a', 'b']


def test_general_handouts_only_for_patients_or_public():
    manifest = {'items': [{'slug': 'pro-only', 'title': '医師向け資料', 'audience': '医師向け'},
                          {'slug': 'sleep', 'title': '眠れないとき', 'audience': '患者さん向け'},
                          {'slug': '../evil', 'title': '不正', 'audience': '患者さん向け'}]}
    rows = general_tools(manifest, CONFIG, {}, '2026-10-21')
    assert rows == [{'url': 'https://tools.ichisouzo-lab.com/handouts/sleep/', 'label': '眠れないとき（配布資料）'}]


# ---- オフライン版 --------------------------------------------------------------

def release(tag, body, name='', assets=('ichisouzo-offline-v1.4-20261019.zip', 'ichisouzo-offline-lite-v1.4-20261019.zip')):
    return {'tag_name': tag, 'name': name, 'body': body, 'draft': False, 'prerelease': False,
            'published_at': '2026-10-18T22:37:34Z', 'html_url': REL + 'tag/' + tag,
            'assets': [{'name': a, 'size': 105270281 if 'lite' not in a else 12366374,
                        'browser_download_url': REL + f'download/{tag}/{a}'} for a in assets]}


def test_offline_release_reads_counts_sizes_and_stated_date():
    body = '# オフライン版 v1.4 — 2026-10-19（日本時間）\n通常版332件（ツール57・症状チェッカー29・ハンドアウト76・図解170）、軽量版162件。'
    data = json.dumps([release('v2-tools', 'x'), release('offline-v1.4', body)])
    off = offline_release(data)
    assert off['version'] == 'v1.4' and off['date'] == '2026-10-19'
    assert off['full']['size_mb'] == 100.4 and off['lite']['size_mb'] == 11.8
    assert off['full']['text'] == '332件：ツール57・症状チェッカー29・ハンドアウト76（HTMLと印刷用PDF）・図解170'
    assert off['lite']['text'] == '162件：ツール57・症状チェッカー29・ハンドアウト76（HTML）。容量の制限が厳しい環境向け'


def test_offline_release_table_format_and_unknown_counts():
    table = '| **通常版** | 84 MB | 322件（ツール55・症状チェッカー29・ハンドアウトHTML74＋PDF74・図解164） |\n| **軽量版** | 6 MB | 158件（ツール55・症状チェッカー29・ハンドアウトHTML74） |'
    off = offline_release(json.dumps([release('offline-v1.3', table)]))
    assert off['date'] == '2026-10-19'  # 本文に日付が無ければ公開日時（日本時間）
    assert off['full']['text'].startswith('322件：ツール55') and off['lite']['text'].startswith('158件：ツール55')
    plain = offline_release(json.dumps([release('offline-v1.5', '説明のみ')]))
    assert '件' not in plain['full']['text']
    with pytest.raises(RuntimeError):
        offline_release(json.dumps([release('offline-v1.6', 'x', assets=('other.zip',))]))


# ---- 最近更新した記事 ----------------------------------------------------------

def page(body, title='記事の題名'):
    return (f'<h1 class="entry-title"><a href="#" class="entry-title-link bookmark">{title}</a></h1>'
            f'<div class="entry-content hatenablog-entry">{body}</div><footer class="entry-footer">'
            '<p>2026年10月20日更新：フッターは見ない</p></footer>')


def test_revision_notice_formats():
    pub, mod = date(2025, 10, 8), date(2026, 10, 15)
    hit = revision_notice(page('<p><strong>2026年10月15日更新：</strong></p><p>挿絵を更新しました。次の文。</p>'), pub, mod, 7)
    assert hit[0] == date(2026, 10, 15) and hit[1] == '挿絵を更新しました。次の文。'
    poems = revision_notice(page('<p>最終確認・改訂日：2026年10月14日（一次文献18件に基づく全面監修を実施）</p>'), pub, mod, 7)
    assert poems[:2] == (date(2026, 10, 14), '一次文献18件に基づく全面監修を実施')
    latest = revision_notice(page('<p>2026年10月9日追記：古い</p><p>【2026年10月12日更新】新しい</p>'), pub, mod, 7)
    assert latest[:2] == (date(2026, 10, 12), '新しい')


@pytest.mark.parametrize('body', [
    '<p>2026年10月1日改訂の電子添文では用量が変わりました。</p>',  # 行頭でない・「〜の」は告知ではない
    '<p>本文の中で 2026年10月15日更新：と書いただけ</p>',
    '<p>2025年10月9日更新：公開直後の修正</p>',  # 公開日から2日未満
    '<p>2026年9月1日更新：今回の更新から遠い古い告知</p>',  # lastmod から7日より前
    '<p>最終確認日：2026年10月15日</p>',  # 確認日は改訂ではない
])
def test_revision_notice_rejects_non_revisions(body):
    assert revision_notice(page(body), date(2025, 10, 8), date(2026, 10, 15), 7) is None


def sitemap_index(mod):
    return ('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap>'
            f'<loc>https://blog.ichisouzo-lab.com/sitemap_periodical.xml?year=2025&amp;month=10</loc><lastmod>{mod}</lastmod>'
            '</sitemap></sitemapindex>')


def urlset(rows):
    return ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + ''.join(f'<url><loc>{u}</loc><lastmod>{m}</lastmod></url>' for u, m in rows) + '</urlset>')


def test_scan_revisions_uses_watermark_limit_and_pending():
    e = 'https://blog.ichisouzo-lab.com/entry/2025/10/0{}/000000'
    rows = [(e.format(1), '2026-10-15T10:00:00+09:00'), (e.format(2), '2026-10-16T10:00:00+09:00'),
            (e.format(3), '2026-10-17T10:00:00+09:00'), (e.format(4), '2026-10-01T10:00:00+09:00'),
            ('https://blog.ichisouzo-lab.com/entry/2026/10/16/000000', '2026-10-16T12:00:00+09:00')]  # 新着は対象外
    fetched = []

    def fetcher(url):
        if 'sitemap' in url:
            return urlset(rows)
        fetched.append(url)
        return page('<p>2026年10月16日更新：内容を見直しました。</p>') if url == e.format(2) else page('<p>本文</p>')

    state = {'revisions': {'watermark': '2026-10-10T00:00:00+09:00'}}
    found = scan_revisions(sitemap_index('2026-10-17T10:00:00+09:00'), state, CONFIG, fetcher, date(2026, 10, 21), sleep=0)
    assert fetched == [e.format(3), e.format(2)]  # 新しい順に上限2件
    assert [f['url'] for f in found] == [e.format(2)] and found[0]['source'] == 'auto' and found[0]['public_verified']
    assert list(state['revisions']['pending']) == [e.format(1)]
    assert state['revisions']['watermark'] == '2026-10-17T10:00:00+09:00'
    # サイトマップが変わらなければ読み直さず、残りだけを取得する。
    fetched.clear()
    scan_revisions(sitemap_index('2026-10-17T10:00:00+09:00'), state, CONFIG, fetcher, date(2026, 10, 21), sleep=0)
    assert fetched == [e.format(1)] and state['revisions']['pending'] == {}


def test_merge_updates_keeps_manual_rows_and_skips_older_or_same_revisions():
    manual = {'id': 'm', 'date': '2026-10-15', 'url': 'https://blog.ichisouzo-lab.com/entry/a', 'title': '手', 'summary': 's',
              'public_verified': True, 'evidence': '手で確認'}
    rows = [manual]
    same = dict(manual, id='auto-1', source='auto')
    newer = dict(manual, id='auto-2', date='2026-10-20', source='auto')
    assert merge_updates(rows, [same, newer]) == [newer]
    assert rows[0] is manual and len(rows) == 2
    assert merge_updates(rows, [newer]) == []
