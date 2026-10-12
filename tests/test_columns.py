import pytest
from portal_columns import render_columns


def item(**changes):
    d={'id':'note-one','date':'2026-10-12','title':'タイトル','body':'第一段落\n\n第二段落','links':[{'label':'記事','url':'https://blog.ichisouzo-lab.com/entry/2026/10/11/025722'}]}
    d.update(changes);return d


def test_text_is_escaped_and_paragraphs_preserved():
    h=render_columns([item(title='<script>',body='A & B\n\n<画像>')])
    assert '<script>' not in h and '&lt;script&gt;' in h
    assert '<p>A &amp; B</p><p>&lt;画像&gt;</p>' in h


def test_invalid_or_duplicate_entries_stop_build():
    for rows in [[item(),item()],[item(date='2026-02-30')],[item(body='')],[item(id='bad id')],[item(links=[{'url':'javascript:alert(1)','label':'bad'}])]]:
        with pytest.raises(ValueError):render_columns(rows)


def test_older_notes_are_available_without_javascript():
    h=render_columns([item(id='note-'+str(i)) for i in range(5)])
    assert h.count('<article ')==5
    assert '以前の制作こぼれ話を読む（2件）' in h
    assert h.index('column-note-2')<h.index('<details')<h.index('column-note-3')
