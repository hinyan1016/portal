"""公開カタログから、日本時間の週ごとに記事・図解・ツールを1件ずつ選ぶ。"""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from html import unescape
from pathlib import PurePosixPath
import re
from urllib.parse import urlsplit

KINDS = ('記事', '図解', 'ツール')
READERS = {'general', 'professional', 'both'}
JST = timezone(timedelta(hours=9))
HISTORY_WEEKS = 8


def week_start(day):
    if isinstance(day, datetime):
        if day.tzinfo is None:
            raise ValueError('日時にはタイムゾーンが必要です')
        day = day.astimezone(JST).date()
    return (day - timedelta(days=day.weekday())).isoformat()


def valid_url(url, kind):
    if not isinstance(url, str):
        return False
    try:
        p = urlsplit(url)
    except ValueError:
        return False
    if p.scheme != 'https' or p.username or p.password or p.query or p.fragment:
        return False
    if kind == '記事':
        return p.netloc == 'blog.ichisouzo-lab.com' and bool(re.fullmatch(r'/entry/\d{4}/\d{2}/\d{2}/\d{6}', p.path))
    if p.netloc != 'tools.ichisouzo-lab.com':
        return False
    pattern = r'/infographics/[a-zA-Z0-9_-]+/' if kind == '図解' else r'/(?!index\.html$)[a-zA-Z0-9_-]+\.html'
    return kind in KINDS and bool(re.fullmatch(pattern, p.path))


def safe_image(value):
    if not isinstance(value, str) or '?' in value or '#' in value or '\\' in value:
        return ''
    p = PurePosixPath(value)
    return value if (not p.is_absolute() and '..' not in p.parts and
                     p.parts and p.parts[0] in ('thumbs', 'assets') and p.suffix in ('.webp', '.png', '.jpg', '.svg')) else ''


def clean_item(raw, today=None):
    if not isinstance(raw, dict) or raw.get('k') not in KINDS or raw.get('a') not in READERS:
        return None
    title, url, kind = raw.get('t'), raw.get('u'), raw['k']
    if not isinstance(title, str) or not title.strip() or not valid_url(url, kind):
        return None
    published = raw.get('d') or ''
    try:
        if published and (date.fromisoformat(published).isoformat() != published or today and published > today.isoformat()):
            return None
    except (ValueError, TypeError):
        return None
    group = raw.get('group')
    if not valid_url(group, '記事'):
        group = url
    return {'t': unescape(unescape(title.strip()))[:500], 'u': url, 'k': kind, 'a': raw['a'],
            'd': published, 'img': safe_image(raw.get('img')), 'group': group}


def validate_selection(selection):
    if not isinstance(selection, dict):
        raise ValueError('週替わりおすすめの情報が必要です')
    day = date.fromisoformat(selection.get('week', ''))
    if day.weekday() != 0 or day.isoformat() != selection['week']:
        raise ValueError('おすすめの週は日本時間の月曜日で指定してください')
    rows = selection.get('items')
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError('記事・図解・ツールを1件ずつ選んでください')
    cleaned = [clean_item(row) for row in rows]
    if any(row is None for row in cleaned) or tuple(row['k'] for row in cleaned) != KINDS:
        raise ValueError('おすすめの形式・読者・公開URLを確認してください')
    if len({row['u'] for row in cleaned}) != 3 or len({row['group'] for row in cleaned}) != 3:
        raise ValueError('おすすめで同じテーマを重複させないでください')
    return {'week': selection['week'], 'items': cleaned}


def update_history(history, selection):
    """1週1行、直近8週だけを保存する。"""
    selection = validate_selection(selection)
    entries = {}
    for entry in history or []:
        if not isinstance(entry, dict):
            continue
        try:
            if date.fromisoformat(entry['week']).weekday() != 0 or entry['week'] > selection['week']:
                continue
            if not isinstance(entry.get('urls'), list) or not isinstance(entry.get('groups'), list):
                continue
        except (ValueError, KeyError, TypeError):
            continue
        entries[entry['week']] = {'week': entry['week'], 'urls': [u for u in entry['urls'] if isinstance(u, str)],
                                  'groups': [g for g in entry['groups'] if isinstance(g, str)]}
    entries[selection['week']] = {'week': selection['week'], 'urls': [x['u'] for x in selection['items']],
                                 'groups': [x['group'] for x in selection['items']]}
    return [entries[key] for key in sorted(entries, reverse=True)[:HISTORY_WEEKS]]


def select_weekly(catalog, previous, history, today, available):
    """週内のURLは固定。非公開化・削除された候補だけは、その週でも差し替える。"""
    if isinstance(today, datetime):
        if today.tzinfo is None:
            raise ValueError('日時にはタイムゾーンが必要です')
        today = today.astimezone(JST).date()
    if not isinstance(catalog, list):
        raise ValueError('公開カタログが必要です')
    week = week_start(today)
    by_kind = {kind: {} for kind in KINDS}
    for raw in catalog:
        item = clean_item(raw, today)
        if item:
            by_kind[item['k']][item['u']] = item
    if any(not rows for rows in by_kind.values()):
        raise ValueError('記事・図解・ツールの公開候補が揃っていません')
    try:
        old = validate_selection(previous)
    except (ValueError, TypeError, KeyError):
        old = None
    fixed = {}
    if old and old['week'] == week:
        for item in old['items']:
            current = by_kind[item['k']].get(item['u'])
            if current and all(current['group'] != other['group'] for other in fixed.values()):
                fixed[item['k']] = current
        if len(fixed) == 3 and len({x['group'] for x in fixed.values()}) == 3:
            return {'week': week, 'items': [dict(fixed[k]) for k in KINDS]}

    recent = [entry for entry in history or [] if isinstance(entry, dict) and
              isinstance(entry.get('week'), str) and entry['week'] <= week]
    recent = sorted(recent, key=lambda x: x['week'], reverse=True)[:HISTORY_WEEKS]
    used_urls, used_groups = set(), set()
    for entry in recent:
        if isinstance(entry.get('urls'), list):
            used_urls.update(u for u in entry['urls'] if isinstance(u, str))
        if isinstance(entry.get('groups'), list):
            used_groups.update(g for g in entry['groups'] if isinstance(g, str))
    previous_urls, previous_groups = set(), set()
    if old:
        previous_urls.update(x['u'] for x in old['items'])
        previous_groups.update(x['group'] for x in old['items'])
        used_urls.update(previous_urls)
        used_groups.update(previous_groups)
    pools = {}
    for kind in KINDS:
        rows = sorted(by_kind[kind].values(), key=lambda x: (x['d'], x['u']), reverse=True)[:100]
        rows.sort(key=lambda x: (x['u'] in previous_urls or x['group'] in previous_groups,
                                x['u'] in used_urls or x['group'] in used_groups,
                                kind == '記事' and x['a'] == 'professional',
                                sha256((week + '\0' + x['u']).encode()).hexdigest()))
        # 週内に一部が消えた場合も、残りの選定を維持する。
        pools[kind] = [fixed[kind]] if kind in fixed else rows
    checked = {}

    def find(index, chosen):
        if index == len(KINDS):
            return chosen
        kind = KINDS[index]
        for item in pools[kind]:
            if any(item['group'] == other['group'] for other in chosen):
                continue
            if kind not in fixed:
                if item['u'] not in checked:
                    if len(checked) >= 12:
                        raise RuntimeError('おすすめのリンク確認上限に達しました')
                    checked[item['u']] = bool(available(item['u']))
                if not checked[item['u']]:
                    continue
            result = find(index + 1, chosen + [dict(item)])
            if result:
                return result
        return None

    chosen = find(0, [])
    if not chosen:
        raise ValueError('テーマが重複せず、開けるおすすめ3件を選べませんでした')
    return validate_selection({'week': week, 'items': chosen})
