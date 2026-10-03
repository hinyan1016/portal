"""カタログに公開用メタデータだけが入ることを検証する。"""
from scripts.refresh_catalog import audience, rss_records, ToolParser, manifest_records, corpus_records, merge_record, inherit_audiences, ArticleMetadataParser, complete_audiences, infer_media_groups, validated_series, apply_series_metadata

def test_audience_does_not_guess_unclassified():
    assert audience('健康のお話', ['医学情報']) == 'unspecified'
    assert audience('医師向けの解説', ['一般向け']) == 'professional'
    assert audience('解説', ['一般向け', '医療従事者向け']) == 'both'

def test_rss_rejects_other_hosts_and_bad_date_is_not_invented():
    xml = '<rss><channel><item><title>A</title><link>https://evil.example/entry/1</link></item><item><title>B</title><link>https://blog.ichisouzo-lab.com/entry/2026/09/01/000000</link><pubDate>invalid</pubDate><category>一般向け</category></item></channel></rss>'
    records = rss_records(xml)
    assert len(records) == 1 and records[0]['d'] == '' and records[0]['a'] == 'general'
    assert set(records[0]) == {'t','u','k','a','d','tags'}

def test_tool_cards_exclude_foreign_links():
    parser = ToolParser()
    parser.feed('<a class="tool-card" href="headache.html"><div class="tool-name">頭痛</div></a><a class="tool-card" href="https://evil.example/a.html"><div class="tool-name">悪意</div></a>')
    assert len(parser.items) == 1
    assert parser.items[0]['u'] == 'https://tools.ichisouzo-lab.com/headache.html'

def test_manifest_validates_slug_and_video_id_and_omits_internal_fields():
    data = {'decks':[{'slug':'../private','title':'Bad'}, {'slug':'safe','title':'安全','source_dir':'private/local/path','youtube_id':'abcdefghijk','blog_url':'https://blog.ichisouzo-lab.com/entry/1','tags':['一般向け'],'slide_count':14}]}
    records = manifest_records(data, 'スライド')
    assert len(records) == 2
    assert records[0]['pages'] == 14
    assert records[1]['k'] == '動画'
    assert all('source_dir' not in x and x['a'] == 'general' for x in records)


def test_explicit_audience_variants_and_topic_tags_are_distinct():
    assert audience('解説', [], '医療者・一般') == 'both'
    assert audience('解説', [], '一般・医療従事者向け') == 'both'
    assert audience('解説', [], '医療者・患者') == 'both'
    assert audience('解説', ['患者・一般']) == 'general'
    assert audience('解説', ['研修医向け']) == 'professional'
    assert audience('解説', ['一般医療機器', '外来患者指導', '医療安全']) == 'unspecified'
    assert audience('解説（一般向け）', []) == 'general'
    assert audience('患者さん向けの資料', []) == 'general'
    assert audience('ご家族向け説明資料', []) == 'general'
    assert audience('非専門医向けの資料', []) == 'professional'
    assert audience('資料【医療者＆患者向け】', []) == 'both'
    assert audience('一般・医療者向け2部構成', []) == 'both'
    assert audience('医療従事者のバーンアウト', []) == 'unspecified'


def test_corpus_requires_public_url_and_explicit_non_draft_and_exports_only_metadata():
    public = 'https://blog.ichisouzo-lab.com/entry/2026/09/01/000000'
    base = {'url': public, 'title': 'A&amp;amp;B', 'categories': ['一般向け'],
            'published': '2026-09-01T00:00:00+09:00', 'draft': 'no',
            'edit_url': 'private/atom/entry/1', 'content': 'private draft content'}
    records = corpus_records([base, {**base, 'draft': 'yes'}, {**base, 'draft': None},
                              {**base, 'url': 'https://blog.ichisouzo-lab.com/entry/private'}], {public})
    assert len(records) == 1
    assert records[0]['t'] == 'A&B'
    assert set(records[0]) == {'t', 'u', 'k', 'a', 'd', 'tags'}


def test_daily_refresh_preserves_supplemented_audience_and_aliases():
    old = {'t': '旧題', 'a': 'general', 'd': '2026-09-01', 'tags': ['一般向け'], 'aliases': ['もの忘れ']}
    fresh = {'t': '新題', 'a': 'unspecified', 'd': '', 'tags': ['認知症']}
    merged = merge_record(old, fresh)
    assert merged == {'t': '新題', 'a': 'general', 'd': '2026-09-01',
                      'tags': ['認知症', '一般向け'], 'aliases': ['もの忘れ']}
    assert merge_record(old, {**fresh, 'a': 'professional'})['a'] == 'professional'


def test_media_inherits_only_known_source_article_and_preserves_own_explicit_audience():
    source = 'https://blog.ichisouzo-lab.com/entry/2026/09/01/000000'
    records = {
        source: {'k': '記事', 'a': 'general'},
        'slide': {'k': 'スライド', 'a': 'unspecified', 'group': source},
        'video': {'k': '動画', 'a': 'professional', 'group': source},
        'missing': {'k': '図解', 'a': 'unspecified', 'group': 'private'},
    }
    assert inherit_audiences(records) == 1
    assert records['slide']['a'] == 'general'
    assert records['video']['a'] == 'professional'
    assert records['missing']['a'] == 'unspecified'
    assert records['slide']['audience_source'] == source
    # 元記事の明示対象が更新されたら、継承値も翌日の更新で追従する。
    records[source]['a'] = 'both'
    assert inherit_audiences(records) == 1
    assert records['slide']['a'] == 'both'
    assert records['video']['a'] == 'professional'


def test_merge_preserves_inheritance_origin_but_direct_metadata_takes_precedence():
    old = {'a': 'general', 'audience_source': 'https://blog.ichisouzo-lab.com/entry/1'}
    assert merge_record(old, {'a': 'unspecified'})['audience_source'] == old['audience_source']
    assert 'audience_source' not in merge_record(old, {'a': 'professional'})


def test_public_article_parser_excludes_sidebar_categories_and_body_audience_mentions():
    parser = ArticleMetadataParser()
    parser.feed('<link rel="canonical" href="https://blog.ichisouzo-lab.com/entry/1">'
                '<header class="entry-header"><h1><a class="entry-title-link">タイトル</a></h1>'
                '<a class="entry-category-link" href="https://blog.ichisouzo-lab.com/archive/category/a">医師向け</a></header>'
                '<div class="entry-content">一般向けの文章も引用</div>'
                '<aside><a class="entry-category-link" href="https://blog.ichisouzo-lab.com/archive/category/b">一般向け</a></aside>')
    assert parser.canonical == 'https://blog.ichisouzo-lab.com/entry/1'
    assert parser.title == 'タイトル'
    assert parser.categories == ['医師向け']


def test_audience_completion_reports_no_explicit_and_failed_without_losing_metadata(monkeypatch):
    records = {
        'known': {'u': 'known', 'k': '記事', 'a': 'general'},
        'new': {'u': 'new', 't': 'N', 'k': '記事', 'a': 'unspecified', 'tags': ['旧分類']},
        'unknown': {'u': 'unknown', 't': 'U', 'k': '記事', 'a': 'unspecified', 'tags': []},
        'failed': {'u': 'failed', 't': 'F', 'k': '記事', 'a': 'unspecified', 'tags': ['保持']},
    }
    def fake_fetch(record):
        if record['u'] == 'failed':
            return None
        return {**record, 'a': 'professional' if record['u'] == 'new' else 'unspecified', 'tags': ['公開分類']}
    monkeypatch.setattr('scripts.refresh_catalog.fetch_article_metadata', fake_fetch)
    summary = complete_audiences(records, workers=2)
    assert summary['checked'] == 3
    assert summary['classified'] == summary['no_explicit_audience'] == summary['failed'] == 1
    assert records['failed']['tags'] == ['保持']
    assert records['new']['tags'] == ['公開分類', '旧分類']


def test_missing_group_uses_unique_public_slug_never_similar_title():
    records = {
        'article': {'k': '記事'},
        'other': {'k': '記事'},
        'figure': {'u': 'https://tools.ichisouzo-lab.com/infographics/exact/', 'k': '図解', 'group': 'article'},
        'slide': {'u': 'https://tools.ichisouzo-lab.com/slides/exact/', 'k': 'スライド', 'group': ''},
        'similar': {'u': 'https://tools.ichisouzo-lab.com/slides/exact-v2/', 'k': 'スライド', 'group': ''},
    }
    assert infer_media_groups(records) == 1
    assert records['slide']['group'] == 'article'
    assert records['slide']['group_source'] == records['figure']['u']
    assert records['similar']['group'] == ''
    assert merge_record(records['slide'], {'group': ''})['group'] == 'article'


def test_series_schema_is_bounded_article_metadata_and_persists_on_refresh():
    series = {'id': 'body-mysteries', 'number': 1, 'proof': 'not exported'}
    assert validated_series(series) == {'id': 'body-mysteries', 'number': 1}
    for invalid in ({'id': 'private', 'number': 1}, {'id': 'body-mysteries', 'number': 0},
                    {'id': 'body-mysteries', 'number': 1000}, {'id': 'body-mysteries', 'number': True},
                    {'id': 'body-mysteries', 'number': '1'}):
        assert validated_series(invalid) is None
    assert merge_record({'series': series}, {'k': '記事'})['series'] == validated_series(series)
    assert 'series' not in merge_record({'series': series}, {'k': 'スライド', 'series': series})


def test_curated_series_never_adds_unpublished_or_media_records():
    public = 'https://blog.ichisouzo-lab.com/entry/2026/04/01/230038'
    private = 'https://blog.ichisouzo-lab.com/entry/private'
    records = {public: {'k': '記事'}, private: {'k': '記事'}, 'slide': {'k': 'スライド'}}
    series = {'id': 'body-mysteries', 'number': 1, 'proof': 'not exported'}
    assert apply_series_metadata(records, {public: series, private: series, 'slide': series}, {public, 'slide'}) == 1
    assert records[public]['series'] == {'id': 'body-mysteries', 'number': 1}
    assert 'series' not in records[private] and 'series' not in records['slide']
