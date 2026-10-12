"""短い制作コラムをJSONから安全な静的HTMLへ変換する。外部サービス不要。"""
from datetime import date
from html import escape
import re
from urllib.parse import urlparse


def render_columns(entries):
    if not isinstance(entries,list):
        raise ValueError('columns.json must contain a list')
    cards=[];seen=set()
    for item in entries:
        key=item.get('id','')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',key) or key in seen:
            raise ValueError('column id must be a unique lowercase slug')
        seen.add(key)
        published=date.fromisoformat(item['date'])
        title=item['title'];body=item['body']
        if not isinstance(title,str) or not title.strip() or not isinstance(body,str) or not body.strip():
            raise ValueError('column title and body are required')
        paragraphs=''.join('<p>'+escape(p.strip())+'</p>' for p in body.split('\n\n') if p.strip())
        links=[]
        for link in item.get('links',[]):
            url=link['url'];label=link['label'];parsed=urlparse(url)
            if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError('column links require a public HTTPS URL')
            if not isinstance(label,str) or not label.strip():
                raise ValueError('column link label is required')
            links.append('<a href="'+escape(url,quote=True)+'" data-track>'+escape(label)+' ↗</a>')
        cards.append('<article class="column-card" id="column-'+key+'" aria-labelledby="column-title-'+key+'">'
                     '<p class="column-meta"><time datetime="'+published.isoformat()+'">'+published.strftime('%Y.%m.%d')+'</time> · 制作メモ</p>'
                     '<h3 id="column-title-'+key+'">'+escape(title)+'</h3>'
                     '<div class="column-body">'+paragraphs+'</div>'
                     '<div class="column-links">'+''.join(links)+'</div></article>')
    if not cards:return '<p class="section-aside">制作メモは準備中です。</p>'
    out='<div class="column-grid">'+''.join(cards[:3])+'</div>'
    if len(cards)>3:
        out+='<details class="columns-archive"><summary>以前の制作こぼれ話を読む（'+str(len(cards)-3)+'件）</summary><div class="column-grid">'+''.join(cards[3:])+'</div></details>'
    return out
