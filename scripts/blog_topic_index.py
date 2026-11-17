"""ブログトップの検索用に、元記事が確認できた公開資料をまとめる。"""
import json
from pathlib import Path

BLOG = 'https://blog.ichisouzo-lab.com/entry/'
TOOLS = 'https://tools.ichisouzo-lab.com/'

# 紹介記事本文で確認した主対象のツール。関連リンク欄の別ツールは含めない。
TOOL_ARTICLES = {
    'warfarin_dose_adjuster.html': '2026/11/16/193218',
    'ncs_report_writer.html': '2026/11/10/072139',
    'aspects_calculator.html': '2026/11/09/150530',
    'eeg_report_writer.html': '2026/11/06/233336',
    'shojo_shoki_helper.html': '2026/11/05/143449',
    'status_epilepticus_initial_calculator.html': '2026/10/31/125736',
    'neuro_exam_helper.html': '2026/10/29/153600',
    'referral_helper.html': '2026/10/29/113816',
    'calorie_protein_calculator.html': '2026/10/29/235254',
    'seizure_lateralization.html': '2026/10/28/142851',
    'stroke_ic_note.html': '2026/10/15/080132',
    'periop_antithrombotic_consult.html': '2026/08/26/110442',
    'spikes_explainer.html': '2026/06/11/185121',
    'ivig_calculator.html': '2026/05/29/234819',
}

# 公開タイトルや医学教育上のテーマに対応する検索用の言い換え。
# 配信時に全タイトルへ適用するので、新着・改訂も毎回の生成に含まれる。
TITLE_ALIASES = {
    '浮腫': ['むくみ', 'むくむ', 'むくんだ'],
    '頭痛': ['頭が痛い', '頭がいたい'],
    '腹痛': ['お腹が痛い', 'おなかが痛い'],
    '胸痛': ['胸が痛い'],
    '呼吸困難': ['息が苦しい', '息苦しい'],
    '振戦': ['手が震える', '手の震え', '手がふるえる'],
    '複視': ['二重に見える', '物が二つに見える'],
    '嚥下': ['飲み込み', '飲みこみ', '飲み込みにくい'],
    '不眠': ['眠れない', '寝つけない', '寝付けない'],
    '便秘': ['便が出ない', '便がでない'],
    'めまい': ['目が回る', '目がまわる'],
    '認知症': ['もの忘れ', '物忘れ'],
    '失神': ['意識を失った', '気を失った'],
    'しびれ': ['痺れ', 'しびれる'],
    '歩行障害': ['歩きにくい', 'うまく歩けない'],
    '抗発作薬': ['抗てんかん薬'], '抗てんかん薬': ['抗発作薬'],
    'ワーファリン': ['ワルファリン', 'warfarin'],
    '低ナトリウム血症': ['低Na', 'ナトリウムが低い'],
    '高カリウム血症': ['高K', 'カリウムが高い'],
    '脳波': ['EEG'], '神経伝導検査': ['NCS'],
    '紹介状': ['診療情報提供書'], '周術期': ['手術前', '手術後'],
}
ARTICLE_ALIASES = {
    '2026/05/06/204047': ['頭を打った', '頭を打つ', '頭をぶつけた', '頭をぶつけて', '頭を打って', '頭部打撲', '頭を打ったあとに気をつけること'],
    '2026/11/16/193218': ['ワルファリンの量を調整したい', 'ワーファリンの量', 'ワルファリンの用量調整', 'PT-INRで用量調整'],
    '2025/05/13/064051': ['救急で使う薬', '救急の薬', '救急薬', '救急で使う薬を復習したい', '救急の薬剤'],
}


def build(items):
    articles = {r['u']: r for r in items if r['k'] == '記事'}
    verified = {TOOLS + tool: BLOG + entry for tool, entry in TOOL_ARTICLES.items()}
    groups = {}
    for row in items:
        parent = row.get('group') or verified.get(row['u'])
        key = parent if parent in articles else row['u']
        groups.setdefault(key, []).append(row)
    topics = []
    for key, members in groups.items():
        root = articles.get(key, members[0])
        titles = list(dict.fromkeys(m['t'] for m in members if m.get('t')))
        aliases = list(ARTICLE_ALIASES.get(key.removeprefix(BLOG), []))
        clinical_titles = ' '.join(titles).replace('咽頭痛', '').replace('喉頭痛', '')
        for word, phrases in TITLE_ALIASES.items():
            if word in clinical_titles:
                aliases.extend(phrases)
        links = []
        for m in members:
            link = {'k': m['k'], 'u': m['u']}
            if m.get('pages'):
                link['p'] = m['pages']
            if m.get('t') and m['t'] != root['t']:
                link['t'] = m['t']
            links.append(link)
        audience = root.get('a')
        if audience == 'unspecified' and 'その症状大丈夫' in root.get('tags', []):
            audience = 'general'
        topics.append({'t': root['t'], 'a': audience, 'links': links,
                       'tags': list(dict.fromkeys(tag for m in members for tag in m.get('tags', []))),
                       'aliases': list(dict.fromkeys(aliases))})
    return topics


def write(destination: Path, root: Path):
    items = json.loads((root / 'search-index.json').read_text(encoding='utf-8'))
    destination.write_text(json.dumps(build(items), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
