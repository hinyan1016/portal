"""公開確認済みの記事改訂を、両トップ用の同じHTMLにする。

台帳には手で登録した行と、scripts/refresh_home.py が公開本文の改訂告知から足した行（source: auto）がある。
日付の上限は日本時間の今日（GitHub Actions は UTC で動くため）。
"""
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
from urllib.parse import urlsplit


def validate(rows):
    if not isinstance(rows, list):
        raise ValueError('更新台帳は配列にしてください')
    seen = set()
    for row in rows:
        for key in ('id', 'date', 'title', 'summary', 'url', 'evidence'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f'{key} が必要です')
        if row['id'] in seen:
            raise ValueError('更新IDが重複しています')
        seen.add(row['id'])
        if date.fromisoformat(row['date']).isoformat() != row['date'] or row['date'] > datetime.now(timezone(timedelta(hours=9))).date().isoformat():
            raise ValueError('更新日は実際の過去または当日の日付にしてください')
        u = urlsplit(row['url'])
        if u.scheme != 'https' or u.netloc != 'blog.ichisouzo-lab.com' or not u.path.startswith('/entry/'):
            raise ValueError('公開ブログ記事のHTTPS URLが必要です')
        if row.get('public_verified') is not True:
            raise ValueError('公開本文との照合が必要です。未公開項目は登録できません')
        if 'updated_at' in row:
            stamp = datetime.fromisoformat(row['updated_at'])
            if stamp.tzinfo is None or stamp.astimezone(timezone(timedelta(hours=9))).date().isoformat() != row['date'] or stamp > datetime.now(timezone.utc):
                raise ValueError('更新時刻はタイムゾーン付きの実際の更新日時にしてください')
    # 同日の実測更新時刻を優先。時刻未記録の既存行同士は従来のID順を保つ。
    def sort_key(row):
        stamp = datetime.fromisoformat(row.get('updated_at', row['date'] + 'T00:00:00+09:00'))
        return row['date'], stamp.timestamp(), row['id']
    return sorted(rows, key=sort_key, reverse=True)


def render(rows):
    rows = validate(rows)
    items = []
    for r in rows:
        items.append('<li><time datetime="{0}">{0} 更新</time><h3><a href="{1}">{2}</a></h3><p>{3}</p></li>'.format(
            escape(r['date']), escape(r['url'], quote=True), escape(r['title']), escape(r['summary'])))
    content = '<ul>' + ''.join(items[:5]) + '</ul>' if items else '<p>現在、掲載する更新情報はありません。</p>'
    if len(items) > 5:
        content += '<details><summary>以前の更新を読む</summary><ul>' + ''.join(items[5:]) + '</ul></details>'
    return '<section class="ics-updates" id="recent-updates" aria-labelledby="recent-updates-title"><h2 id="recent-updates-title">最近更新した記事</h2><p>公開済みの記事に加えた変更を、更新日の順にご案内します。</p>' + content + '</section>'


def build(root):
    rows = json.loads((root / 'article-updates.json').read_text(encoding='utf-8'))
    section = render(rows)
    css = (root / 'article-updates.css').read_text(encoding='utf-8')
    page = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>最近更新した記事｜医知創造ラボ</title><link rel="canonical" href="https://ichisouzo-lab.com/article-updates.html"><style>body{margin:0;font-family:system-ui,sans-serif;background:#fff;color:#21332f}' + css + '</style><main>' + section + '<p style="padding:1rem"><a href="https://ichisouzo-lab.com/">総合ホームへ</a> · <a href="https://blog.ichisouzo-lab.com/">ブログへ</a></p></main></html>'
    (root / 'article-updates.html').write_text(page, encoding='utf-8', newline='\n')
    # 台帳の照合メモは配信せず、エスケープ済みの表示部品だけを公開する。
    js = "(function(){'use strict';if(location.pathname!=='/'||location.search)return;var host=document.getElementById('ics-updates-host');if(!host||host.getAttribute('data-loaded'))return;var style=document.createElement('style');style.textContent=" + json.dumps(css, ensure_ascii=False) + ";document.head.appendChild(style);host.innerHTML=" + json.dumps(section, ensure_ascii=False) + ";host.hidden=false;host.setAttribute('data-loaded','true');})();"
    (root / 'article-updates-widget.js').write_text(js, encoding='utf-8', newline='\n')
    return section
