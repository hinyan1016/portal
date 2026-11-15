"""ブログトップ第5段（タブ即時切替・押せる動画/スライド・最新解説枠・実績バッジ）用フィード生成。

search-index.json（約0.8MB）全体を読まずに済むよう、最新医療記事（各タブ12件）、
メディア詳細（YouTube ID・スライドslug・枚数）、最新スライド特集4件、統計だけを
blog-home-feed.json（60KB未満）にまとめる。stage_site.py が公開のたびに再生成する。
"""
from __future__ import annotations

from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ENTRY_RE = re.compile(r'https://blog\.ichisouzo-lab\.com/entry/(\d{4}/\d{2}/\d{2}/\d{6})')
THUMB_RE = re.compile(r'thumbs/[A-Za-z0-9/_.-]+\.webp')
VIDEO_RE = re.compile(r'https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})')
SLIDE_RE = re.compile(r'https://tools\.ichisouzo-lab\.com/slides/([A-Za-z0-9_-]+)/')

EXCLUDE_WORDS = (
    '宗教', '世代区分', 'イシガメ', 'ギャンブル', '沼・池・湖',
    '観光ガイド', 'モデルコース', '米子', 'ガチャ', '聖地',
    'パチンコ', '競馬', '旅・地域', 'ポケモン', 'アニメ', 'グルメ', '温泉',
    '魚の分類', '日本の世代',
)

CLINICAL_MED_CATS = frozenset({
    '医学情報', '脳神経内科', 'てんかん', '脳卒中', '認知症',
    '頭痛', 'パーキンソン病', '内科', '感染症', '生活習慣病',
    '糖尿', '薬', '栄養', 'アンチエイジング', '初期研修医',
    '医学教育', '医療安全', 'ガイドライン解説', '20年の変遷シリーズ',
    'その症状大丈夫', 'セルフチェック',
})


def is_medical_article(item: dict) -> bool:
    """除外語を含まず、臨床医学カテゴリーを1つ以上持つ記事かを判定する。"""
    title = str(item.get('t') or '')
    tags = [str(tag) for tag in (item.get('tags') or [])]
    haystack = title + ' ' + ' '.join(tags)
    if any(word in haystack for word in EXCLUDE_WORDS):
        return False
    return bool(set(tags) & CLINICAL_MED_CATS)


def _valid_thumb(img: str, thumbs_dir: Path | None) -> str:
    if not isinstance(img, str) or not THUMB_RE.fullmatch(img) or '..' in img:
        return ''
    if thumbs_dir is not None and not (thumbs_dir.parent / img).is_file():
        return ''
    return img


def _clean_cats(tags: list[str], extra_prefix: str | None = None) -> list[str]:
    cats = list(dict.fromkeys(str(t).strip() for t in tags if str(t).strip()))
    if extra_prefix and extra_prefix not in cats:
        cats.insert(0, extra_prefix)
    if len(cats) > 1 and '医学情報' in cats:
        cats = [c for c in cats if c != '医学情報']
    return cats or (['医学情報'] if '医学情報' in tags else [])


def build_media_detail(items: list[dict]) -> dict[str, dict]:
    """記事キーごとの動画ID・スライドslug・ページ数を抽出する。"""
    media: dict[str, dict] = {}
    for item in items:
        kind = item.get('k')
        group_m = ENTRY_RE.fullmatch(str(item.get('group') or ''))
        if not group_m:
            continue
        key = group_m.group(1)
        url = str(item.get('u') or '')
        if kind == '動画':
            vm = VIDEO_RE.fullmatch(url)
            if vm:
                entry = media.setdefault(key, {})
                entry.setdefault('v', vm.group(1))
        elif kind == 'スライド':
            sm = SLIDE_RE.fullmatch(url)
            if sm:
                entry = media.setdefault(key, {})
                entry.setdefault('s', sm.group(1))
                pages = item.get('pages')
                if isinstance(pages, int) and not isinstance(pages, bool) and pages > 0:
                    entry.setdefault('p', pages)
    return media


def build_feed(
    items: list[dict],
    stats: dict | None = None,
    thumbs_dir: Path | None = None,
    feed_limit: int = 12,
    showcase_limit: int = 4,
) -> dict:
    """公開カタログと統計から第5段用の軽量フィード辞書を組み立てる。"""
    media = build_media_detail(items)
    stats_in = stats if isinstance(stats, dict) else {}

    def _stat_int(name: str, fallback: int) -> int:
        val = stats_in.get(name)
        return val if isinstance(val, int) and not isinstance(val, bool) and val >= 0 else fallback

    articles_count = sum(1 for it in items if it.get('k') == '記事')
    videos_count = sum(1 for it in items if it.get('k') == '動画')
    slides_count = sum(1 for it in items if it.get('k') == 'スライド')
    tools_count = sum(1 for it in items if it.get('k') == 'ツール')
    infographics_count = sum(1 for it in items if it.get('k') == '図解')

    out_stats = {
        'articles': _stat_int('articles', articles_count),
        'videos': videos_count,
        'slides': _stat_int('slides', slides_count),
        'tools': _stat_int('tools', tools_count),
        'infographics': _stat_int('infographics', infographics_count),
    }

    medical_rows: list[tuple[str, dict, str, str, list[str], str]] = []
    seen_keys: set[str] = set()
    for item in items:
        if item.get('k') != '記事':
            continue
        m = ENTRY_RE.fullmatch(str(item.get('u') or ''))
        if not m:
            continue
        key = m.group(1)
        if key in seen_keys or not is_medical_article(item):
            continue
        seen_keys.add(key)
        title = str(item.get('t') or '').strip()
        date_str = str(item.get('d') or '').strip()
        tags = [str(t).strip() for t in (item.get('tags') or []) if str(t).strip()]
        img = _valid_thumb(str(item.get('img') or ''), thumbs_dir)
        medical_rows.append((key, item, title, date_str, tags, img))

    def _row_to_entry(row: tuple[str, dict, str, str, list[str], str], extra_prefix: str | None = None) -> dict:
        key, _item, title, date_str, tags, img = row
        return {
            'id': key,
            't': title,
            'd': date_str,
            'cats': _clean_cats(tags, extra_prefix=extra_prefix),
            'img': img,
        }

    feeds_all = [_row_to_entry(r) for r in medical_rows[:feed_limit]]

    feeds_doctor: list[dict] = []
    for row in medical_rows:
        _key, item, _title, _date_str, tags, _img = row
        if (
            '医師向け' in tags
            or item.get('a') in ('professional', 'both')
            or bool({'初期研修医', '医学教育', 'ガイドライン解説'} & set(tags))
        ):
            feeds_doctor.append(_row_to_entry(row, extra_prefix='医師向け'))
            if len(feeds_doctor) >= feed_limit:
                break

    feeds_general: list[dict] = []
    for row in medical_rows:
        _key, item, _title, _date_str, tags, _img = row
        if (
            '一般向け' in tags
            or '患者さん向け' in tags
            or 'その症状大丈夫' in tags
            or item.get('a') in ('general', 'both')
        ):
            has_gen = any(c in tags for c in ('一般向け', '患者さん向け', 'その症状大丈夫'))
            feeds_general.append(_row_to_entry(row, extra_prefix=None if has_gen else '一般向け'))
            if len(feeds_general) >= feed_limit:
                break

    feeds_media: list[dict] = []
    for row in medical_rows:
        if row[0] in media:
            feeds_media.append(_row_to_entry(row))
            if len(feeds_media) >= feed_limit:
                break

    showcase: list[dict] = []
    for key, item, title, date_str, tags, img in medical_rows:
        info = media.get(key)
        if not info or 's' not in info:
            continue
        aud = ''
        if '医師向け' in tags or item.get('a') in ('professional', 'both'):
            aud = '医師向け'
        elif any(c in tags for c in ('一般向け', '患者さん向け', 'その症状大丈夫')) or item.get('a') == 'general':
            aud = '一般向け'
        showcase.append({
            'id': key,
            't': title,
            'd': date_str,
            'aud': aud,
            's': info['s'],
            'p': info.get('p', 0),
            'v': info.get('v', ''),
            'img': img,
        })
        if len(showcase) >= showcase_limit:
            break

    return {
        'v': 1,
        'base': 'https://ichisouzo-lab.com/',
        'stats': out_stats,
        'media': media,
        'feeds': {
            'all': feeds_all,
            'doctor': feeds_doctor,
            'general': feeds_general,
            'media': feeds_media,
        },
        'showcase': showcase,
    }


def write(out_path: Path | str, root: Path = ROOT) -> int:
    items = json.loads((root / 'search-index.json').read_text(encoding='utf-8'))
    stats_path = root / 'stats.json'
    stats = json.loads(stats_path.read_text(encoding='utf-8')) if stats_path.exists() else {}
    data = build_feed(items, stats=stats, thumbs_dir=root / 'thumbs')
    Path(out_path).write_text(
        json.dumps(data, ensure_ascii=False, separators=(',', ':')),
        encoding='utf-8',
    )
    return len(data['media'])


if __name__ == '__main__':
    print(write(ROOT / 'blog-home-feed.json'), 'media entries')
