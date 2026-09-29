"""カタログに公開用メタデータだけが入ることを検証する。"""
from scripts.refresh_catalog import audience, rss_records, ToolParser, manifest_records

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
