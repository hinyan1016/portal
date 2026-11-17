from scripts.blog_topic_index import BLOG, TOOLS, build


def test_media_and_verified_tool_join_only_a_published_article():
    article_url = BLOG + '2026/11/16/193218'
    article = {'k': '記事', 't': 'ワーファリン用量調整', 'u': article_url}
    tool = {'k': 'ツール', 't': '用量調整', 'u': TOOLS + 'warfarin_dose_adjuster.html'}
    slide = {'k': 'スライド', 't': '解説', 'u': TOOLS + 'slides/example/', 'group': article_url, 'pages': 13}
    other = {'k': '記事', 't': article['t'], 'u': BLOG + '2025/05/29/140015'}
    linked, separate = build([tool, slide, other, article])
    assert linked['t'] == article['t'] and 'ワルファリン' in linked['aliases']
    assert len(linked['links']) == 3 and linked['links'][1]['p'] == 13
    assert separate['links'] == [{'k': '記事', 'u': other['u']}]
    assert len(build([tool, slide])) == 2


def test_new_titles_receive_search_phrases_without_a_topic_override():
    rows = [{'k': '記事', 't': title, 'u': BLOG + str(i)} for i, title in enumerate(['浮腫の評価', '咽頭痛'])]
    edema, sore_throat = build(rows)
    assert 'むくみ' in edema['aliases'] and '頭が痛い' not in sore_throat['aliases']
