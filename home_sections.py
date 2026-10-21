"""トップの自動更新枠（医学の新着・ツールの近道・オフライン版）を home-feed.json から静的HTMLにする。

データは scripts/refresh_home.py が公開情報だけから作る。ここでは URL の行き先と形式を
検証してからエスケープして埋め込み、想定外の値は index.html を書き換えずに失敗させる。
"""
from datetime import date
from html import escape
import re
from urllib.parse import urlsplit

BLOG_ENTRY = 'https://blog.ichisouzo-lab.com/entry/'
TOOLS_HOST = 'tools.ichisouzo-lab.com'
RELEASE_PREFIX = 'https://github.com/hinyan1016/medical-ddx-tools/releases/'
VIDEO_ID = re.compile(r'[\w-]{11}')
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
        if audience:
            meta += ' · ' + escape(_text(audience, 'audience_label'))
        links = f'<a data-track href="{u}" aria-label="{escape(title, quote=True)}の記事を読む">記事を読む →</a>'
        if video:
            links += (f'<a data-track href="https://www.youtube.com/watch?v={video}" '
                      f'aria-label="{escape(title, quote=True)}の解説動画をYouTubeで見る">解説動画を見る ↗</a>')
        cards.append(f'<article class="medical-news-card"><p class="medical-news-date">{meta}</p>'
                     f'<h3><a data-track href="{u}">{t}</a></h3><p>{escape(summary)}</p>'
                     f'<div class="medical-news-links">{links}</div></article>')
    return '<div class="medical-news-grid">' + ''.join(cards) + '</div>'


def render_tool_shortcuts(items):
    if not isinstance(items, list) or not items:
        raise ValueError('ツールの近道が空です')
    links = []
    for item in items:
        url = _https(item.get('url'), 'url', host=TOOLS_HOST)
        links.append(f'<a data-track href="{escape(url, quote=True)}">{escape(_text(item.get("label"), "label"))} <span>↗</span></a>')
    return '<div class="tool-shortcuts">' + ''.join(links) + '</div>'


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
    if not any(marker in page for marker in MARKERS):
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
    return page
