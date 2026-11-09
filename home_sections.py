"""トップの自動更新枠（医学の新着・ツールの近道・オフライン版）を home-feed.json から静的HTMLにする。

データは scripts/refresh_home.py が公開情報だけから作る。ここでは URL の行き先と形式を
検証してからエスケープして埋め込み、想定外の値は index.html を書き換えずに失敗させる。
"""
from datetime import date
from html import escape
from pathlib import Path
import re
from urllib.parse import urlsplit

from weekly_picks import validate_selection

BLOG_ENTRY = 'https://blog.ichisouzo-lab.com/entry/'
TOOLS_HOST = 'tools.ichisouzo-lab.com'
RELEASE_PREFIX = 'https://github.com/hinyan1016/medical-ddx-tools/releases/'
VIDEO_ID = re.compile(r'[\w-]{11}')
WEEKLY_PICKS_MARKER = '<!-- WEEKLY_PICKS -->'
LATEST_VIDEOS_MARKER = '<!-- LATEST_VIDEOS -->'
MARKERS = ('<!-- MEDICAL_NEWS -->', '<!-- PRO_TOOL_SHORTCUTS -->', '<!-- GENERAL_TOOL_SHORTCUTS -->',
           '<!-- OFFLINE_ASIDE -->', '<!-- OFFLINE_CARDS -->', '<!-- OFFLINE_RELEASE_LINK -->')


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} が必要です')
    return value.strip()


def _https(url, name, host=None, prefix=None):
    url = _text(url, name)
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.username or parts.password:
        raise ValueError(f'{name} は公開HTTPSのURLにしてください')
    if host and parts.netloc != host:
        raise ValueError(f'{name} の行き先が想定外です')
    if prefix and not url.startswith(prefix):
        raise ValueError(f'{name} の行き先が想定外です')
    return url


def render_medical_news(items):
    if not isinstance(items, list) or not items:
        raise ValueError('医学の新着が空です')
    cards = []
    for item in items:
        title = _text(item.get('title'), 'title')
        url = _https(item.get('url'), 'url', prefix=BLOG_ENTRY)
        day = date.fromisoformat(_text(item.get('date'), 'date'))
        summary = _text(item.get('summary'), 'summary')
        audience = item.get('audience_label', '')
        video = item.get('video', '')
        if video and not VIDEO_ID.fullmatch(video):
            raise ValueError('動画IDの形式が想定外です')
        t, u = escape(title), escape(url, quote=True)
        meta = f'<time datetime="{day.isoformat()}">{day.strftime("%Y/%m/%d")}</time> 公開'
        reader = ''
        if audience:
            reader = ' · ' + escape(_text(audience, 'audience_label'))
        links = f'<a data-track href="{u}" aria-label="{escape(title, quote=True)}の記事を読む">記事を読む →</a>'
        if video:
            links += (f'<a data-track href="https://www.youtube.com/watch?v={video}" '
                      f'aria-label="{escape(title, quote=True)}の解説動画をYouTubeで見る">解説動画を見る ↗</a>')
        cards.append(f'<article class="medical-news-card" data-home-url="{u}"><p class="medical-news-date" '
                     f'data-audience-label="{escape(audience, quote=True)}">{meta}<span class="home-news-reader">{reader}</span></p>'
                     f'<h3><a data-track href="{u}" title="{escape(title, quote=True)}">{t}</a></h3><p>{escape(summary)}</p>'
                     f'<div class="medical-news-links">{links}</div></article>')
    return '<div class="medical-news-grid">' + ''.join(cards) + '</div>'


def render_home_updates(rows):
    """トップは直近3件に絞り、更新台帳とブログ用ウィジェットの全文は保持する。"""
    from article_updates import validate
    items = []
    for row in validate(rows)[:3]:
        url = escape(row['url'], quote=True)
        items.append(f'<li data-home-url="{url}"><time datetime="{escape(row["date"])}">'
                     f'{escape(row["date"])} 更新</time><h4><a data-track href="{url}">'
                     f'{escape(row["title"])}</a></h4><p>{escape(row["summary"])}</p></li>')
    content = '<ul class="home-updates-list">' + ''.join(items) + '</ul>'
    return ('<section class="home-updates" id="recent-updates" aria-labelledby="recent-updates-title">'
            '<h3 class="home-panel-title" id="recent-updates-title">最近更新した記事</h3>'
            '<p class="home-feed-note">既存記事の改訂を、更新日の順に掲載しています。</p>' + content +
            '<p class="home-feed-empty" hidden>この読者区分の更新記事はありません。</p>'
            '<a class="quiet-link home-updates-more" href="article-updates.html">更新履歴をすべて見る →</a></section>')


def render_tool_shortcuts(items):
    if not isinstance(items, list) or not items:
        raise ValueError('ツールの近道が空です')
    links = []
    for item in items:
        url = _https(item.get('url'), 'url', host=TOOLS_HOST)
        links.append(f'<a data-track href="{escape(url, quote=True)}">{escape(_text(item.get("label"), "label"))} <span>↗</span></a>')
    return '<div class="tool-shortcuts">' + ''.join(links) + '</div>'


def render_latest_videos(items):
    """最新の解説動画の棚。データが無いときは空にする（見出しと登録リンクだけが残る）。"""
    if not isinstance(items, list) or not items:
        return ''
    cards = []
    for item in items[:3]:
        if not isinstance(item, dict):
            raise ValueError('動画の行の形式が想定外です')
        video = _text(item.get('id'), 'id')
        if not VIDEO_ID.fullmatch(video):
            raise ValueError('動画IDの形式が想定外です')
        title = _text(item.get('title'), 'title')
        day = date.fromisoformat(_text(item.get('date'), 'date'))
        thumb = f'https://i.ytimg.com/vi/{video}/'
        cards.append(
            f'<a class="home-video" data-track href="https://www.youtube.com/watch?v={video}" '
            f'aria-label="{escape(title, quote=True)}をYouTubeで見る">'
            f'<span class="home-video-thumb"><img src="{thumb}mqdefault.jpg" '
            f'srcset="{thumb}mqdefault.jpg 320w, {thumb}hqdefault.jpg 480w" sizes="(max-width:680px) 160px, 380px" '
            'alt="" width="320" height="180" loading="lazy" decoding="async"></span>'
            f'<span class="home-video-body"><time datetime="{day.isoformat()}">{day.strftime("%Y/%m/%d")} 公開</time>'
            f'<span class="home-video-title">{escape(title)}</span></span></a>'
        )
    return '<div class="home-videos-grid">' + ''.join(cards) + '</div>'


def render_weekly_picks(selection):
    selection = validate_selection(selection)
    readers = {'general': '一般の方・ご家族', 'professional': '医療従事者向け', 'both': '一般・医療従事者'}
    captions = {'記事': ('記事で詳しく確認できます。', '記事を読む →'),
                '図解': ('全体像を一枚の図解で確認できます。', '図解を見る ↗'),
                'ツール': ('診療や学習に役立つツールです。', 'ツールを使う ↗')}
    icons = {'記事': '<path d="M4 4h7a3 3 0 0 1 3 3v14a4 4 0 0 0-4-3H4ZM14 7a3 3 0 0 1 3-3h5v14h-4a4 4 0 0 0-4 3M7 8h3M7 12h3M17 8h2M17 12h2"/>',
             '図解': '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="2"/><path d="m4 18 6-6 4 4 3-3 4 5"/>',
             'ツール': '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6M9 11h6M9 15h2M14 15h1"/>'}
    cards = []
    for row in selection['items']:
        url, title, kind = escape(row['u'], quote=True), escape(row['t'], quote=True), row['k']
        image = row['img']
        if image and (Path(__file__).resolve().parent / image).is_file():
            visual = (f'<div class="home-pick-image"><img src="{escape(image, quote=True)}" width="160" height="160" '
                      f'alt="" loading="lazy" decoding="async" data-fallback-url="{url}"></div>')
        else:
            visual = f'<div class="home-pick-image home-pick-placeholder" aria-hidden="true"><svg viewBox="0 0 24 24">{icons[kind]}</svg></div>'
        caption, cta = captions[kind]
        cards.append(f'<article class="home-pick" data-home-reader="{row["a"]}" data-pick-kind="{kind}">'
                     f'<a class="home-pick-main" data-track href="{url}" title="{title}">{visual}<div>'
                     f'<p class="home-pick-meta">{kind} · {readers[row["a"]]}</p><h3>{title}</h3>'
                     f'<p class="home-pick-reason">{caption}</p><span class="home-pick-cta">{cta}</span></div></a></article>')
    week = selection['week']
    return (f'<p class="home-feed-note weekly-picks-note"><time datetime="{week}">{week.replace("-", "/")}の週</time>'
            ' · 記事・図解・ツールを週替わりで紹介します。</p>'
            f'<div class="home-picks-grid" data-pick-week="{week}">' + ''.join(cards) + '</div>')


def _download_card(edition, label, heading, button):
    url = _https(edition.get('url'), 'url', prefix=RELEASE_PREFIX + 'download/')
    size = edition.get('size_mb')
    if not isinstance(size, (int, float)) or size <= 0:
        raise ValueError('ZIPの大きさが想定外です')
    return (f'<article class="download-card"><span class="label">{label}</span><h3>{heading}</h3>'
            f'<p>{escape(_text(edition.get("text"), "text"))}</p>'
            f'<a class="button {button}" href="{escape(url, quote=True)}" download>ダウンロード <span>ZIP・{size:.1f} MB</span></a></article>')


def render_offline(offline):
    if not isinstance(offline, dict):
        raise ValueError('オフライン版の情報が必要です')
    version = _text(offline.get('version'), 'version')
    if not re.fullmatch(r'v\d+(?:\.\d+)*', version):
        raise ValueError('オフライン版の版番号が想定外です')
    day = date.fromisoformat(_text(offline.get('date'), 'date'))
    release = _https(offline.get('release_url'), 'release_url', prefix=RELEASE_PREFIX + 'tag/')
    aside = f'<p class="section-aside">最新版 {version}（{day.year}年{day.month}月{day.day}日）</p>'
    cards = ('<div class="download-cards">'
             + _download_card(offline.get('full') or {}, '通常版', 'すべて入り', 'primary')
             + _download_card(offline.get('lite') or {}, '軽量版', '図解・PDFなし', 'secondary')
             + '</div>')
    link = f'<p class="download-more"><a class="quiet-link" href="{escape(release, quote=True)}">収録内容と更新履歴 <span>↗</span></a></p>'
    return aside, cards, link


def apply(page, feed):
    """マーカーを置き換える。マーカーが無い旧テンプレートはそのまま返す。"""
    if not any(marker in page for marker in MARKERS + (WEEKLY_PICKS_MARKER, LATEST_VIDEOS_MARKER)):
        return page
    for marker in MARKERS:
        if page.count(marker) != 1:
            raise ValueError(f'{marker} はトップに1つだけ置いてください')
    aside, cards, link = render_offline(feed.get('offline'))
    parts = {
        '<!-- MEDICAL_NEWS -->': render_medical_news(feed.get('medical_news')),
        '<!-- PRO_TOOL_SHORTCUTS -->': render_tool_shortcuts(feed.get('pro_tools')),
        '<!-- GENERAL_TOOL_SHORTCUTS -->': render_tool_shortcuts(feed.get('general_tools')),
        '<!-- OFFLINE_ASIDE -->': aside, '<!-- OFFLINE_CARDS -->': cards, '<!-- OFFLINE_RELEASE_LINK -->': link,
    }
    for marker, html in parts.items():
        page = page.replace(marker, html, 1)
    if WEEKLY_PICKS_MARKER in page:
        if page.count(WEEKLY_PICKS_MARKER) != 1:
            raise ValueError('おすすめの目印はトップに1つだけ置いてください')
        page = page.replace(WEEKLY_PICKS_MARKER, render_weekly_picks(feed.get('weekly_picks')), 1)
    if LATEST_VIDEOS_MARKER in page:
        if page.count(LATEST_VIDEOS_MARKER) != 1:
            raise ValueError('最新動画の目印はトップに1つだけ置いてください')
        page = page.replace(LATEST_VIDEOS_MARKER, render_latest_videos(feed.get('latest_videos')), 1)
    return page
