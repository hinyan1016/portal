"""統合ポータル（医知創造ラボ）の index.html を生成するスクリプト。

入力: corpus_cache.json（正準ブログデータ）と medical-ddx-tools/ の走査結果。
出力: portal/index.html（単一ファイル・CSS/JS内包）。
デザインは Claude Design ハンドオフ（2026-07-04 トップページ改善）準拠。
"""
import html as html_lib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote


# ---- データ読込・集計 -------------------------------------------------------

def load_corpus(path):
    """corpus_cache.json を読み込んで list[record] を返す。"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def published_records(records):
    """下書き(draft=='yes')を除いた公開レコードのリストを返す。"""
    return [r for r in records if r.get("draft") != "yes"]


def count_categories(records):
    """レコード群の categories を集計して Counter を返す。"""
    c = Counter()
    for r in records:
        for cat in (r.get("categories") or []):
            c[cat] += 1
    return c


def hatena_category_url(blog_base, category):
    """はてなの自動カテゴリページURLを返す（カテゴリ名はURLエンコード）。"""
    return f"{blog_base}/archive/category/{quote(category)}"


def latest_articles(records, n):
    """公開レコードを published 降順に並べ、先頭 n 件を返す。"""
    pub = published_records(records)
    pub.sort(key=lambda r: r.get("published", ""), reverse=True)
    return pub[:n]


# 「一般向け」カテゴリが付いた記事のみ一般読者向けとみなし、それ以外（医師向け／初期研修医／
# 読者タグ無し）は医療従事者向けに分類する。読者タグの付与が不徹底（約半数が無タグ）で、
# 無タグの新着は実態として医療従事者向けが大半のため、この既定が最新記事を最も正しく振り分ける。
GENERAL_CATEGORY = "一般向け"

# タイトルに専門家向けマーカー（【脳神経内科医向け】等）があれば、カテゴリに「一般向け」が
# 誤って付いていても医療従事者側に分類する。「医向け」は「〜科医向け」「研修医向け」を包含する。
PRO_TITLE_MARKERS = ("医療従事者向け", "医師向け", "医向け")


def is_general_reader(record):
    """記事が一般読者向け（GENERAL_CATEGORY 付き）なら True。

    ただしタイトルに専門家向けマーカーが含まれる記事は、タグに関わらず False。
    """
    title = record.get("title") or ""
    if any(m in title for m in PRO_TITLE_MARKERS):
        return False
    return GENERAL_CATEGORY in (record.get("categories") or [])


def split_by_audience(articles):
    """記事リストを (医療従事者向け, 一般向け) の2つのリストに分割して返す（順序保持）。"""
    professional = [a for a in articles if not is_general_reader(a)]
    general = [a for a in articles if is_general_reader(a)]
    return professional, general


# ---- ツール／インフォ／スライド走査 -----------------------------------------

def scan_tools(tools_dir):
    """ツールディレクトリ直下の *.html（index.html除く）をソートして返す。"""
    p = Path(tools_dir)
    if not p.is_dir():
        return []
    return sorted(f.name for f in p.glob("*.html") if f.name != "index.html")


def _subsite_dirs(parent_dir):
    """index.html を含み、'_' で始まらないサブフォルダの Path を返す（未ソート）。"""
    p = Path(parent_dir)
    if not p.is_dir():
        return []
    return [d for d in p.iterdir()
            if d.is_dir() and not d.name.startswith("_") and (d / "index.html").exists()]


def scan_subsites(parent_dir):
    """親ディレクトリ直下で index.html を含むサブフォルダ名（slug）をソートして返す。

    '_template' などアンダースコア始まりの補助フォルダは除外する。
    """
    return sorted(d.name for d in _subsite_dirs(parent_dir))


def recent_subsites(parent_dir, n):
    """index.html の更新時刻が新しい順にサブフォルダ名を最大 n 件返す。"""
    dirs = _subsite_dirs(parent_dir)
    dirs.sort(key=lambda d: (d / "index.html").stat().st_mtime, reverse=True)
    return [d.name for d in dirs[:n]]


# ---- 公開マニフェスト（infographics/slides の正準カタログ） ------------------

def load_manifest_entries(manifest_path, key):
    """manifest.json の配列（infographics="items" / slides="decks"）を返す。

    ファイルが無い・壊れている・slug 欠落の項目は安全側に落とす（空リスト/除外）。
    マニフェストは公開カタログの正準データ源（各 index 一覧ページもここから生成される）。
    """
    p = Path(manifest_path)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    entries = data.get(key) or []
    return [e for e in entries if isinstance(e, dict) and e.get("slug")]


def manifest_slugs(entries):
    """マニフェスト項目を新しい順の slug リストにして返す。

    date フィールドがあれば date 降順（安定ソートなので同日・date無しは
    マニフェスト順を保持）。無ければ「新規は先頭に追加」の規約どおり元の順。
    """
    if any(e.get("date") for e in entries):
        entries = sorted(entries, key=lambda e: e.get("date") or "", reverse=True)
    return [e["slug"] for e in entries]


def manifest_labels(entries):
    """マニフェストの {slug: 短い表示名} を返す（title を short_label で短縮）。"""
    out = {}
    for e in entries:
        label = short_label(e.get("title"))
        if label:
            out[e["slug"]] = label
    return out


# ページの <title> 抽出用
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def page_title(index_path):
    """index.html の <title> テキストを返す（無ければ None）。"""
    p = Path(index_path)
    if not p.is_file():
        return None
    m = TITLE_RE.search(p.read_text(encoding="utf-8"))
    return m.group(1).strip() if m else None


def clean_page_title(title):
    """<title> から定型句（早見インフォグラフィック/スライド資料）とブランドを除いた表示名を返す。

    例: "細胞外液補充液の使い分け 早見インフォグラフィック｜… ― 医知創造ラボ" -> "細胞外液補充液の使い分け"
        "「自律神経失調症」と言われたら | スライド資料" -> "「自律神経失調症」と言われたら"
    空なら None。
    """
    t = (title or "").strip()
    for marker in ["医知創造ラボ", "早見インフォグラフィック", "インフォグラフィック", "スライド資料"]:
        idx = t.find(marker)
        if idx != -1:
            t = t[:idx]
    t = t.rstrip(" 　|｜―—・:：")
    return t or None


def short_label(title):
    """ブログ風の長いタイトルをチップ表示用に短縮する（clean + 「｜」以降を除去）。

    例: "高血圧の生活指導｜減塩・家庭血圧・運動を1枚に（インフォグラフィック）"
        -> "高血圧の生活指導"
    """
    t = clean_page_title(title)
    if not t:
        return None
    t = t.split("｜")[0].rstrip(" 　|｜―—・:：（(")
    return t or None


def parse_subsite_labels(parent_dir):
    """サブサイト群の {slug: 表示名} を返す（各 index.html の <title> をクリーニング）。"""
    out = {}
    for d in _subsite_dirs(parent_dir):
        label = clean_page_title(page_title(d / "index.html"))
        if label:
            out[d.name] = label
    return out


# medical-ddx-tools/index.html のツールカードから href→絵文字→名前 を抽出する正規表現
TOOL_CARD_RE = re.compile(
    r'<a class="tool-card" href="([^"]+\.html)">\s*'
    r'<div class="tool-emoji">([^<]*)</div>\s*'
    r'<div class="tool-name">([^<]*)</div>'
)


def parse_tool_labels(index_path):
    """ツール一覧 index.html を解析し {filename: {"name", "emoji"}} を返す。

    日本語のツール名は medical-ddx-tools/index.html のカードが正式名。
    そこから取得することで、手動マッピング不要・ツール追加時も自動反映される。
    """
    p = Path(index_path)
    if not p.is_file():
        return {}
    text = p.read_text(encoding="utf-8")
    out = {}
    for href, emoji, name in TOOL_CARD_RE.findall(text):
        out[href] = {"name": name.strip(), "emoji": emoji.strip()}
    return out


# ---- HTML描画 ---------------------------------------------------------------

def render_category_card(label, count, url):
    """カテゴリ1件分のチップHTMLを返す。"""
    safe = html_lib.escape(label)
    return (
        f'<a class="chip" href="{url}">{safe}'
        f'<span class="chip-count">{count}</span></a>'
    )


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#1B3A5C">
<meta name="description" content="{{tagline}}">
<title>{{brand}}｜医療と健康の知のハブ</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%231B3A5C'/%3E%3Cpath d='M13 6h6v7h7v6h-7v7h-6v-7H6v-6h7z' fill='%23fff'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=BIZ+UDPGothic:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{--navy:#1B3A5C;--blue:#2C5AA0;--ink:#222;--muted:#5A6B7E;--bg:#F4F6F8;--line:#dee2e6;--line2:#D0D8E4;--chip:#E8F0FE;--green:#1E7A3C;--greenbg:#E9F7EE;--orange:#E8850C;--orangebg:#FDF3E7;--orangetx:#A85E06;--num:'Segoe UI',sans-serif;--shadow:0 2px 8px rgba(27,58,92,.10)}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'BIZ UDPGothic','Yu Gothic',Meiryo,'Noto Sans JP',sans-serif;color:var(--ink);background:var(--bg);line-height:1.7;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
@keyframes fadeIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.topnav{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.97);border-bottom:1px solid var(--line2);box-shadow:0 2px 8px rgba(27,58,92,.08)}
.topnav .wrap{height:60px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{display:flex;align-items:center;gap:10px}
.brand-mark{display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,var(--navy),var(--blue));color:#fff;font-size:16px;font-weight:700}
.brand-name{font-size:18px;font-weight:700;color:var(--navy);letter-spacing:.02em}
.topnav nav{display:flex;align-items:center;gap:4px;font-size:14px}
.topnav nav a{color:var(--navy);padding:8px 12px;border-radius:8px;transition:.15s}
.topnav nav a:hover{background:var(--chip);color:var(--blue)}
.topnav nav a.yt{color:#fff;background:var(--blue);padding:8px 16px;border-radius:20px;font-weight:700}
.topnav nav a.yt:hover{background:var(--navy)}
.hero{background:linear-gradient(135deg,#1B3A5C 0%,#2C5AA0 100%);color:#fff;padding:64px 24px 56px}
.hero-inner{max-width:1080px;margin:0 auto;animation:fadeIn .4s ease}
.badge{display:inline-block;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.35);font-size:13px;padding:5px 14px;border-radius:20px;letter-spacing:.04em}
.hero h1{margin:20px 0 12px;font-size:44px;line-height:1.25;letter-spacing:.02em;font-weight:700}
.hero .tagline{margin:0 0 24px;font-size:18px;color:rgba(255,255,255,.9);max-width:560px}
.search{position:relative;max-width:560px;margin:0 0 28px;z-index:40}
.search input{width:100%;padding:13px 20px;border:0;border-radius:8px;font-size:16px;box-shadow:0 4px 16px rgba(0,0,0,.18);outline:none;color:var(--ink);font-family:inherit}
.results{position:absolute;left:0;right:0;top:calc(100% + 8px);background:#fff;border-radius:12px;box-shadow:0 16px 44px rgba(27,58,92,.30);overflow:hidden;max-height:62vh;overflow-y:auto;z-index:60}
.results a{display:flex;align-items:center;gap:10px;padding:11px 16px;border-bottom:1px solid #EEF2F6;color:var(--ink);font-size:14px}
.results a:last-child{border-bottom:0}
.results a:hover{background:#F4F8FE}
.results .k{font-size:11px;font-weight:700;color:#fff;background:var(--blue);border-radius:10px;padding:2px 8px;white-space:nowrap;flex:none}
.results .ft{color:var(--blue);font-weight:700}
.results .empty{padding:14px 16px;color:var(--muted);font-size:14px}
.cta{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:36px}
.cta a{display:inline-block;font-weight:700;font-size:15px;padding:12px 28px;border-radius:8px;transition:.15s}
.cta .primary{background:#fff;color:var(--navy);box-shadow:0 4px 16px rgba(27,58,92,.18)}
.cta .primary:hover{transform:translateY(-3px);box-shadow:0 6px 20px rgba(27,58,92,.3)}
.cta .ghost{color:#fff;border:1px solid rgba(255,255,255,.6)}
.cta .ghost:hover{background:rgba(255,255,255,.12);transform:translateY(-3px)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;max-width:720px}
.stat{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.22);border-radius:8px;padding:14px 16px}
.stat-num{display:block;font-family:var(--num);font-size:26px;font-weight:700;line-height:1.2}
.stat-label{display:block;font-size:13px;color:rgba(255,255,255,.85)}
.section{max-width:1080px;margin:0 auto;padding:56px 24px 8px}
.sec-head{display:flex;align-items:baseline;gap:12px;margin-bottom:6px}
.sec-eyebrow{font-family:var(--num);font-size:13px;font-weight:700;letter-spacing:.08em;color:var(--blue);text-transform:uppercase}
.sec-head h2{margin:0;font-size:26px;color:var(--navy)}
.sec-sub{margin:0 0 24px;font-size:14px;color:var(--muted)}
.latest-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}
.latest-col{background:#fff;border:1px solid var(--line);border-radius:8px;box-shadow:var(--shadow);overflow:hidden}
.latest-head{padding:12px 20px;display:flex;align-items:center;gap:8px}
.latest-head .em{font-size:16px}
.latest-tag{font-size:14px;font-weight:700}
.latest-head-pro{background:var(--chip)}
.latest-tag-pro{color:var(--blue)}
.latest-head-gen{background:var(--greenbg)}
.latest-tag-gen{color:var(--green)}
.latest-list{display:flex;flex-direction:column}
.latest-item{display:block;padding:13px 20px;border-top:1px solid #EEF2F6;font-size:14px;line-height:1.55}
.latest-col-pro .latest-item:hover{background:#F4F8FE;color:var(--blue)}
.latest-col-gen .latest-item:hover{background:#F4FBF6;color:var(--green)}
.cat-stack{display:grid;grid-template-columns:1fr;gap:16px}
.cat-card{background:#fff;border:1px solid var(--line);border-radius:8px;padding:20px 24px;box-shadow:var(--shadow)}
.cat-title{font-size:15px;font-weight:700;color:var(--navy);margin-bottom:12px}
.chip-row{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:inline-flex;align-items:baseline;gap:6px;border-radius:20px;border:1px solid transparent;transition:.15s}
.chip-count{font-family:var(--num);font-size:12px;font-weight:400}
.cat-group-0{border-left:4px solid var(--blue)}
.cat-group-0 .chip{background:var(--chip);color:var(--blue);font-size:14px;font-weight:700;padding:8px 16px}
.cat-group-0 .chip:hover{border-color:var(--blue);transform:translateY(-2px)}
.cat-group-0 .chip-count{color:var(--muted)}
.cat-group-1{border-left:4px solid var(--navy)}
.cat-group-1 .chip{background:var(--bg);color:var(--navy);font-size:14px;padding:7px 14px;border-color:var(--line2)}
.cat-group-1 .chip:hover{background:var(--chip);border-color:var(--blue);color:var(--blue)}
.cat-group-1 .chip-count{color:var(--muted)}
.cat-group-2{border-left:4px solid var(--orange)}
.cat-group-2 .chip{background:var(--orangebg);color:var(--orangetx);font-size:14px;font-weight:700;padding:8px 16px}
.cat-group-2 .chip:hover{border-color:var(--orange);transform:translateY(-2px)}
.cat-group-2 .chip-count{color:#B98547}
.tool-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:16px}
.tool-card{display:flex;flex-direction:column;gap:8px;background:#fff;border:2px solid var(--line);border-radius:8px;padding:20px;box-shadow:var(--shadow);transition:.15s}
.tool-card:hover{border-color:var(--blue);transform:translateY(-3px);box-shadow:0 6px 16px rgba(27,58,92,.16)}
.tool-emoji{font-size:28px}
.tool-name{font-size:15px;font-weight:700;color:var(--navy);line-height:1.5}
.tool-go{font-size:13px;color:var(--blue)}
.wide-links{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.wide-link{display:flex;align-items:center;justify-content:space-between;gap:12px;border-radius:8px;padding:16px 20px;transition:.15s}
.wide-link span{font-size:14px;font-weight:700}
.wide-link .arrow{font-weight:700}
.wide-blue{background:var(--chip);border:1px solid #C8DAF5}
.wide-blue span{color:var(--blue)}
.wide-blue:hover{border-color:var(--blue)}
.wide-green{background:var(--greenbg);border:1px solid #BFE5CC}
.wide-green span{color:var(--green)}
.wide-green:hover{border-color:#28A745}
.visual-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}
.visual-card{background:#fff;border:1px solid var(--line);border-radius:8px;box-shadow:var(--shadow);padding:20px 24px}
.visual-title{font-size:15px;font-weight:700;color:var(--navy);margin-bottom:14px}
.ig-chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.ig-chip{display:inline-block;background:var(--bg);color:var(--navy);font-size:13px;padding:6px 12px;border-radius:6px;border:1px solid var(--line2);line-height:1.5;transition:.15s}
.ig-chip:hover{background:var(--chip);border-color:var(--blue);color:var(--blue)}
.visual-links{display:flex;flex-direction:column;gap:6px;font-size:14px}
.visual-links a{color:var(--blue)}
.visual-links a:hover{text-decoration:underline}
.visual-links .strong{font-weight:700}
.slide-list{display:flex;flex-direction:column;margin-bottom:12px}
.slide-item{display:block;padding:10px 0;border-bottom:1px solid #EEF2F6;font-size:14px;line-height:1.5}
.slide-item:hover{color:var(--blue)}
.slide-all{font-size:14px;color:var(--blue);font-weight:700}
.slide-all:hover{text-decoration:underline}
.duo-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:stretch}
.yt-card{display:flex;flex-direction:column;justify-content:center;gap:10px;background:linear-gradient(135deg,var(--navy),var(--blue));border-radius:8px;padding:28px;box-shadow:0 4px 16px rgba(27,58,92,.18);transition:.15s}
.yt-card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(27,58,92,.28)}
.yt-eyebrow{font-family:var(--num);font-size:13px;font-weight:700;letter-spacing:.08em;color:rgba(255,255,255,.75);text-transform:uppercase}
.yt-title{font-size:20px;font-weight:700;color:#fff}
.yt-sub{font-size:14px;color:rgba(255,255,255,.85)}
.about-card{background:#fff;border:1px solid var(--line);border-left:4px solid var(--blue);border-radius:8px;padding:24px 28px;box-shadow:var(--shadow)}
.about-eyebrow{font-family:var(--num);font-size:13px;font-weight:700;letter-spacing:.08em;color:var(--blue);text-transform:uppercase;margin-bottom:8px}
.about-title{font-size:16px;font-weight:700;color:var(--navy);margin-bottom:8px}
.about-card p{margin:0;font-size:14px;color:#333;line-height:1.8}
.about-link{display:inline-block;margin-top:12px;font-size:14px;color:var(--blue);font-weight:700}
.about-link:hover{text-decoration:underline}
footer{margin-top:64px;background:var(--navy);color:#fff;padding:40px 24px 32px}
.foot-inner{max-width:1080px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
.foot-top{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px}
.foot-brand{display:flex;align-items:center;gap:10px;font-size:16px;font-weight:700}
.foot-mark{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:6px;background:rgba(255,255,255,.15);font-size:14px}
footer nav{display:flex;flex-wrap:wrap;gap:8px;font-size:14px}
footer nav a{color:rgba(255,255,255,.85);padding:6px 10px;border-radius:6px}
footer nav a:hover{background:rgba(255,255,255,.12);color:#fff}
.disc{margin:0;font-size:12px;color:rgba(255,255,255,.6);border-top:1px solid rgba(255,255,255,.15);padding-top:16px}
@media(max-width:860px){.latest-grid,.visual-grid,.duo-grid,.wide-links{grid-template-columns:1fr}.tool-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:720px){.hero{padding:48px 18px 42px}.hero h1{font-size:32px}.hero .tagline{font-size:16px}.stats{grid-template-columns:repeat(2,1fr)}.sec-head h2{font-size:22px}.section{padding:44px 18px 8px}.topnav .wrap{height:auto;flex-wrap:wrap;justify-content:center;padding:10px 16px}.topnav nav{gap:0;font-size:13px;flex-wrap:wrap;justify-content:center}.topnav nav a{padding:6px 8px}.topnav nav a.yt{padding:6px 12px}.tool-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header class="topnav"><div class="wrap">
<a class="brand" href="https://ichisouzo-lab.com/"><span class="brand-mark">✚</span><span class="brand-name">{{brand}}</span></a>
<nav>
<a href="#blog">記事</a>
<a href="#tools">診断ツール</a>
<a href="#visuals">図解・スライド</a>
<a href="{{check_url}}">セルフチェック</a>
<a class="yt" href="{{youtube_url}}">YouTube</a>
</nav>
</div></header>
<section class="hero"><div class="hero-inner">
<span class="badge">🧠 脳神経内科専門医が運営</span>
<h1>{{brand}}</h1>
<p class="tagline">{{tagline}}</p>
<div class="search"><input id="q" type="search" autocomplete="off" placeholder="記事・ツール・動画を検索…" aria-label="サイト内検索"><div id="results" class="results" hidden></div></div>
<div class="cta">
<a class="primary" href="#blog">記事を探す</a>
<a class="ghost" href="{{tools_url}}">診断ツール</a>
<a class="ghost" href="{{check_url}}">症状セルフチェック</a>
</div>
<div class="stats">{{stats_html}}</div>
</div></section>
<main>
<section class="section" id="latest">
<div class="sec-head"><span class="sec-eyebrow">Latest</span><h2>最新の記事</h2></div>
<p class="sec-sub">ブログの新着記事を自動で表示しています。</p>
<div id="latest-wrap" class="latest-grid">{{latest_html}}</div>
</section>
<section class="section" id="blog">
<div class="sec-head"><span class="sec-eyebrow">Articles</span><h2>ブログ記事を探す</h2></div>
<p class="sec-sub">読者・テーマ・シリーズから、目的の記事へ。</p>
<div class="cat-stack">{{category_groups_html}}</div>
</section>
<section class="section" id="tools">
<div class="sec-head"><span class="sec-eyebrow">Tools</span><h2>診断ツール・セルフチェック</h2></div>
<p class="sec-sub">臨床の鑑別を支援するインタラクティブツールと、一般の方向けの症状チェック。</p>
{{tools_html}}
</section>
<section class="section" id="visuals">
<div class="sec-head"><span class="sec-eyebrow">Visuals</span><h2>インフォグラフィック・スライド</h2></div>
<p class="sec-sub">要点を一枚で。図解とスライド資料。</p>
{{visual_html}}
</section>
<section class="section" id="youtube">
<div class="duo-grid">
<a class="yt-card" href="{{youtube_url}}">
<span class="yt-eyebrow">YouTube</span>
<span class="yt-title">▶ 動画で学ぶ「{{brand}}」チャンネル</span>
<span class="yt-sub">医療・健康の解説動画を配信中。チャンネルを見る →</span>
</a>
<div class="about-card">
<div class="about-eyebrow">About</div>
<div class="about-title">🧠 監修：脳神経内科専門医</div>
<p>{{intro}}</p>
<a class="about-link" href="comment.html">監修者からのコメントを読む →</a>
</div>
</div>
</section>
</main>
<footer><div class="foot-inner">
<div class="foot-top">
<div class="foot-brand"><span class="foot-mark">✚</span><span>{{brand}}</span></div>
<nav><a href="https://blog.ichisouzo-lab.com">ブログ</a><a href="{{tools_url}}">診断ツール</a><a href="{{check_url}}">症状チェック</a><a href="{{youtube_url}}">YouTube</a></nav>
</div>
<p class="disc">⚠️ 本サイトの情報は一般的な医療情報であり、個別の診断・治療に代わるものではありません。</p>
</div></footer>
<script>
(function(){var i=document.getElementById('q'),b=document.getElementById('results'),x=null,l=false,t;
var C={'記事':'#2C5AA0','ツール':'#1B3A5C','図解':'#E8850C','スライド':'#2E7D62'};
function e(s){return (s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function ld(){if(x||l)return;l=true;fetch('search-index.json').then(function(res){return res.json();}).then(function(d){x=d;render(i.value);}).catch(function(){l=false;});}
function ft(q){return '<a class="ft" href="https://blog.ichisouzo-lab.com/search?q='+encodeURIComponent(q)+'">「'+e(q)+'」をブログ全文検索 →</a>';}
function render(q){q=(q||'').trim();if(!q){b.hidden=true;b.innerHTML='';return;}if(!x){b.hidden=false;b.innerHTML='<div class="empty">読み込み中…</div>';ld();return;}var n=q.toLowerCase(),h=[];for(var k=0;k<x.length&&h.length<20;k++){if((x[k].t||'').toLowerCase().indexOf(n)>=0)h.push(x[k]);}var o='';h.forEach(function(m){o+='<a href="'+m.u+'"><span class="k" style="background:'+(C[m.k]||'#2C5AA0')+'">'+m.k+'</span><span>'+e(m.t)+'</span></a>';});if(!h.length){o+='<div class="empty">該当する見出しがありません。全文検索をお試しください。</div>';}o+=ft(q);b.innerHTML=o;b.hidden=false;}
i.addEventListener('focus',ld);
i.addEventListener('input',function(){clearTimeout(t);t=setTimeout(function(){render(i.value);},120);});
i.addEventListener('keydown',function(ev){if(ev.key==='Enter'){var f=b.querySelector('a');if(f){window.location.href=f.getAttribute('href');}}});
document.addEventListener('click',function(ev){if(!ev.target.closest('.search')){b.hidden=true;}});})();
(function(){var w=document.getElementById('latest-wrap');if(!w)return;var PER=6;
function e(s){return (s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
// 「一般向け」カテゴリの記事のみ一般読者向け。それ以外（医師向け／読者タグ無し）は医療従事者向け。
// ただしタイトルに【〜医向け】等の専門家向けマーカーがあれば、タグの誤付与に関わらず医療従事者側。
function isProTitle(t){return t.indexOf('医療従事者向け')>=0||t.indexOf('医師向け')>=0||t.indexOf('医向け')>=0;}
function grp(label,emoji,cls,arr){if(!arr.length)return '';var c='';for(var j=0;j<arr.length&&j<PER;j++){c+='<a class="latest-item" href="'+arr[j].u+'">'+e(arr[j].t)+'</a>';}
return '<div class="latest-col latest-col-'+cls+'"><div class="latest-head latest-head-'+cls+'"><span class="em">'+emoji+'</span><span class="latest-tag latest-tag-'+cls+'">'+label+'</span></div><div class="latest-list">'+c+'</div></div>';}
fetch('https://blog.ichisouzo-lab.com/rss').then(function(r){return r.text();}).then(function(x){
var doc=new DOMParser().parseFromString(x,'application/xml');var it=doc.querySelectorAll('item');var pro=[],gen=[];
for(var k=0;k<it.length;k++){var t=it[k].querySelector('title'),l=it[k].querySelector('link');if(!t||!l||!l.textContent.trim())continue;
var cats=it[k].querySelectorAll('category'),isGen=false;for(var m=0;m<cats.length;m++){if(cats[m].textContent.trim()==='一般向け'){isGen=true;break;}}
if(isProTitle(t.textContent||''))isGen=false;
(isGen?gen:pro).push({t:t.textContent,u:l.textContent.trim()});}
if(!pro.length&&!gen.length)return;
w.innerHTML=grp('医療従事者向け','🩺','pro',pro)+grp('一般の方向け','🏠','gen',gen);
}).catch(function(){});})();
// インフォグラフィック/スライドの新着を公開マニフェスト(tools側 manifest.json)から実行時取得。
// 新コンテンツはマニフェスト先頭に追加されるため、ポータルの再ビルド不要で自動的に最新化される。
// 取得失敗時はビルド時HTMLがそのまま残る（フォールバック）。
(function(){var TOOLS='{{tools_url}}';
function e(s){return (s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function clean(t){t=(t||'');var M=['医知創造ラボ','早見インフォグラフィック','インフォグラフィック','スライド資料'];
for(var i=0;i<M.length;i++){var p=t.indexOf(M[i]);if(p!==-1)t=t.slice(0,p);}
var q=t.indexOf('｜');if(q!==-1)t=t.slice(0,q);
return t.replace(/[ 　|｜―—・:：（(]+$/,'');}
function setStat(k,v){var s=document.querySelector('[data-stat="'+k+'"]');if(s)s.textContent=String(v);}
fetch(TOOLS+'/infographics/manifest.json').then(function(r){return r.json();}).then(function(m){
var it=(m.items||[]).filter(function(x){return x&&x.slug;});if(!it.length)return;
it.sort(function(a,b){return (b.date||'').localeCompare(a.date||'');});
var el=document.getElementById('ig-chips');
if(el){var o='';for(var i=0;i<it.length&&i<{{ig_recent_n}};i++){
o+='<a class="ig-chip" href="'+TOOLS+'/infographics/'+encodeURIComponent(it[i].slug)+'/">'+e(clean(it[i].title)||it[i].slug)+'</a>';}
el.innerHTML=o;}
setStat('infographics',it.length);
}).catch(function(){});
fetch(TOOLS+'/slides/manifest.json').then(function(r){return r.json();}).then(function(m){
var dk=(m.decks||[]).filter(function(x){return x&&x.slug;});if(!dk.length)return;
var el=document.getElementById('slide-list');
if(el){var o='';for(var i=0;i<dk.length&&i<{{slide_recent_n}};i++){
o+='<a class="slide-item" href="'+TOOLS+'/slides/'+encodeURIComponent(dk[i].slug)+'/">'+e(clean(dk[i].title)||dk[i].slug)+'</a>';}
el.innerHTML=o;}
var a=document.getElementById('slide-all');if(a)a.textContent='全スライド（'+dk.length+'本）を見る →';
setStat('slides',dk.length);
}).catch(function(){});})();
</script>
</body>
</html>"""


def render_page(ctx):
    """コンテキスト辞書から完成HTMLを返す。未指定キーは空文字（数値系は既定値）。"""
    keys = ["brand", "tagline", "intro", "stats_html", "youtube_url", "tools_url",
            "check_url", "category_groups_html", "latest_html", "tools_html", "visual_html",
            "ig_recent_n", "slide_recent_n"]
    defaults = {"ig_recent_n": "12", "slide_recent_n": "8"}
    out = PAGE_TEMPLATE
    for k in keys:
        out = out.replace("{{" + k + "}}", str(ctx.get(k, defaults.get(k, ""))))
    return out


# ---- セクション組立 ---------------------------------------------------------

def build_stats_html(published, tools, slides, infographics):
    """ヒーローの統計セル（記事数・ツール数など）のHTMLを生成。"""
    items = [(f"{published:,}", "公開記事", "articles"), (str(tools), "診断ツール", "tools"),
             (str(slides), "スライド", "slides"),
             (str(infographics), "インフォグラフィック", "infographics")]
    return "".join(
        f'<div class="stat"><span class="stat-num" data-stat="{key}">{n}</span>'
        f'<span class="stat-label">{label}</span></div>'
        for n, label, key in items
    )


def build_search_index(pub, tool_files, tool_labels, ig_slugs, ig_labels,
                        slide_slugs, slide_labels, tools_url):
    """全コンテンツ横断検索用のインデックス list[{"t","u","k"}] を生成。

    t=タイトル, u=URL, k=種別（記事/ツール/図解/スライド）。タイトル検索用。
    """
    idx = []
    for r in pub:
        idx.append({"t": r.get("title", ""), "u": r.get("url", ""), "k": "記事"})
    for fn in tool_files:
        name = (tool_labels.get(fn) or {}).get("name") or fn.replace(".html", "")
        idx.append({"t": name, "u": f"{tools_url}/{fn}", "k": "ツール"})
    for slug in ig_slugs:
        idx.append({"t": ig_labels.get(slug) or slug,
                    "u": f"{tools_url}/infographics/{slug}/", "k": "図解"})
    for slug in slide_slugs:
        idx.append({"t": slide_labels.get(slug) or slug,
                    "u": f"{tools_url}/slides/{slug}/", "k": "スライド"})
    return idx


def build_category_groups_html(groups, counts, blog_base):
    """設定のカテゴリグループからHTMLを生成。件数0のカテゴリはスキップ。

    グループごとに cat-group-{i} クラスを付け、CSS側で
    読者別=青／テーマ=紺／シリーズ=オレンジ の配色を切り替える。
    """
    parts = []
    for i, g in enumerate(groups):
        cards = []
        for cat in g["categories"]:
            n = counts.get(cat, 0)
            if n <= 0:
                continue
            cards.append(render_category_card(cat, n, hatena_category_url(blog_base, cat)))
        if cards:
            parts.append(
                f'<div class="cat-card cat-group-{i}">'
                f'<div class="cat-title">▶ {html_lib.escape(g["title"])}</div>'
                f'<div class="chip-row">{"".join(cards)}</div></div>'
            )
    return "".join(parts)


def _latest_items(articles):
    """記事リストを行リンクHTML（latest-list 内の <a>）に変換する。"""
    rows = []
    for a in articles:
        t = html_lib.escape(a.get("title", ""))
        rows.append(f'<a class="latest-item" href="{a.get("url", "")}">{t}</a>')
    return "".join(rows)


def _latest_group_html(label_text, emoji, key, articles):
    """1グループ（見出し帯＋行リンク列）のHTMLを返す。記事が無ければ空文字。

    key は 'pro'/'gen'。CSSクラス latest-col-{key}/latest-head-{key}/latest-tag-{key} に対応。
    """
    if not articles:
        return ""
    return (
        f'<div class="latest-col latest-col-{key}">'
        f'<div class="latest-head latest-head-{key}"><span class="em">{emoji}</span>'
        f'<span class="latest-tag latest-tag-{key}">{label_text}</span></div>'
        f'<div class="latest-list">{_latest_items(articles)}</div>'
        f'</div>'
    )


def build_latest_html(articles, per_group=6):
    """最新記事を「医療従事者向け」「一般の方向け」の2カラムに分けたHTMLを生成する。"""
    if not articles:
        return ""
    professional, general = split_by_audience(articles)
    return (
        _latest_group_html("医療従事者向け", "🩺", "pro", professional[:per_group])
        + _latest_group_html("一般の方向け", "🏠", "gen", general[:per_group])
    )


def build_tools_html(tool_files, tools_url, featured, labels=None,
                     total=None, check_url=None):
    """代表ツール（featured優先・無ければ先頭数件）のカードHTMLを生成。

    labels に日本語名があればそれ（絵文字付き）を表示し、無ければファイル名にフォールバック。
    total と check_url が与えられれば「すべての診断ツール」「症状セルフチェッカー」の
    ワイドリンク2枚を末尾に付ける。
    """
    labels = labels or {}
    picks = [t for t in featured if t in tool_files] or tool_files[:6]
    cards = []
    for fn in picks:
        info = labels.get(fn)
        if info and info.get("name"):
            emoji = html_lib.escape(info.get("emoji", "")) or "🧩"
            name = html_lib.escape(info["name"])
        else:
            emoji = "🧩"
            name = html_lib.escape(fn.replace(".html", ""))
        cards.append(
            f'<a class="tool-card" href="{tools_url}/{fn}">'
            f'<span class="tool-emoji">{emoji}</span>'
            f'<span class="tool-name">{name}</span>'
            f'<span class="tool-go">ツールを開く →</span></a>'
        )
    out = f'<div class="tool-grid">{"".join(cards)}</div>'
    if total is not None and check_url:
        out += (
            '<div class="wide-links">'
            f'<a class="wide-link wide-blue" href="{tools_url}">'
            f'<span>🔍 すべての診断ツールを見る（{total}ツール）</span>'
            f'<span class="arrow">→</span></a>'
            f'<a class="wide-link wide-green" href="{check_url}">'
            f'<span>✅ 症状セルフチェッカーを開く（一般の方向け）</span>'
            f'<span class="arrow">→</span></a></div>'
        )
    return out


def build_subsite_cards(slugs, tools_url, sub, labels, item_class="ig-chip"):
    """サブサイト（infographics/slides）のリンクHTML群を生成。

    labels に日本語名があればそれを、無ければ slug を表示。リンクは {tools_url}/{sub}/{slug}/。
    item_class でチップ型（ig-chip）とリスト行型（slide-item）を切り替える。
    """
    cards = []
    for slug in slugs:
        label = html_lib.escape(labels.get(slug) or slug)
        cards.append(f'<a class="{item_class}" href="{tools_url}/{sub}/{slug}/">{label}</a>')
    return "".join(cards)


def build_visual_html(ig_slugs, ig_labels, slide_slugs, slide_labels, slide_total, tools_url,
                      gallery_count=0):
    """インフォグラフィック（チップ）＋スライド（行リスト）の2カラムHTMLを生成。"""
    ig_chips = build_subsite_cards(ig_slugs, tools_url, "infographics", ig_labels, "ig-chip")
    slide_items = build_subsite_cards(slide_slugs, tools_url, "slides", slide_labels,
                                      "slide-item")
    gallery_link = ""
    if gallery_count:
        gallery_link = (f'<a href="{tools_url}/infographics-gallery/">'
                        f'画像版インフォグラフィック集（{gallery_count}点）→</a>')
    return (
        '<div class="visual-grid">'
        '<div class="visual-card">'
        '<div class="visual-title">📋 インフォグラフィック（新着）</div>'
        f'<div class="ig-chips" id="ig-chips">{ig_chips}</div>'
        f'<div class="visual-links">'
        f'<a class="strong" href="{tools_url}/infographics/">インフォグラフィック一覧を見る →</a>'
        f'{gallery_link}</div></div>'
        '<div class="visual-card">'
        '<div class="visual-title">🖥️ スライド資料（新着）</div>'
        f'<div class="slide-list" id="slide-list">{slide_items}</div>'
        f'<a class="slide-all" id="slide-all" href="{tools_url}/slides/">全スライド（{slide_total}本）を見る →</a>'
        '</div></div>'
    )


def main():
    here = Path(__file__).resolve().parent          # portal/
    workspace = here.parent                          # Claude_task_new/
    config = json.loads((here / "config.json").read_text(encoding="utf-8"))
    featured = json.loads((here / "featured.json").read_text(encoding="utf-8"))

    records = load_corpus(workspace / config["corpus_path"])
    pub = published_records(records)
    counts = count_categories(pub)

    tools_dir = workspace / config["tools_dir"]
    tool_files = scan_tools(tools_dir)
    tool_labels = parse_tool_labels(tools_dir / "index.html")

    # 新着・総数は公開マニフェスト（一覧ページと同じ正準カタログ）を第一データ源とし、
    # マニフェストが無い場合のみディレクトリ走査(mtime)にフォールバックする。
    ig_n = config.get("infographics_recent_count", 12)
    ig_dir = tools_dir / "infographics"
    ig_slugs = scan_subsites(ig_dir)
    ig_manifest = load_manifest_entries(ig_dir / "manifest.json", "items")
    ig_order = manifest_slugs(ig_manifest)
    ig_recent = ig_order[:ig_n] if ig_order else recent_subsites(ig_dir, ig_n)
    ig_labels = parse_subsite_labels(ig_dir)
    ig_disp = {**ig_labels, **manifest_labels(ig_manifest)}
    ig_total = len(ig_order) if ig_order else len(ig_slugs)

    slide_n = config.get("slides_recent_count", 8)
    slide_dir = tools_dir / "slides"
    slide_manifest = load_manifest_entries(slide_dir / "manifest.json", "decks")
    slide_order = manifest_slugs(slide_manifest)
    slide_recent = slide_order[:slide_n] if slide_order else recent_subsites(slide_dir, slide_n)
    slide_labels = parse_subsite_labels(slide_dir)
    slide_disp = {**slide_labels, **manifest_labels(slide_manifest)}
    slide_all = scan_subsites(slide_dir)
    slide_total = len(slide_order) if slide_order else len(slide_all)

    gallery_json = tools_dir / "infographics-gallery" / "gallery.json"
    gallery_count = 0
    if gallery_json.is_file():
        try:
            gallery_count = len(json.loads(gallery_json.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            gallery_count = 0

    ctx = {
        "brand": config["brand"],
        "tagline": config["tagline"],
        "intro": config.get("intro", ""),
        "stats_html": build_stats_html(len(pub), len(tool_files), slide_total, ig_total),
        "youtube_url": config["youtube_url"],
        "tools_url": config["tools_url"],
        "check_url": config["check_url"],
        "category_groups_html": build_category_groups_html(
            config["category_groups"], counts, config["blog_base"]),
        "latest_html": build_latest_html(latest_articles(pub, 40),
                                          config.get("latest_per_group", 6)),
        "tools_html": build_tools_html(tool_files, config["tools_url"],
                                       featured.get("featured_tools", []), tool_labels,
                                       total=len(tool_files), check_url=config["check_url"]),
        "visual_html": build_visual_html(ig_recent, ig_disp, slide_recent, slide_disp,
                                         slide_total, config["tools_url"], gallery_count),
        "ig_recent_n": str(ig_n),
        "slide_recent_n": str(slide_n),
    }
    out = render_page(ctx)
    (here / "index.html").write_text(out, encoding="utf-8", newline="\n")

    search_index = build_search_index(pub, tool_files, tool_labels, ig_slugs, ig_labels,
                                       slide_all, slide_labels, config["tools_url"])
    (here / "search-index.json").write_text(
        json.dumps(search_index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8", newline="\n")

    print(f"Wrote {here / 'index.html'} ({len(out)} bytes); "
          f"published={len(pub)}, tools={len(tool_files)}, "
          f"infographics={len(ig_slugs)}, slides={slide_total}, "
          f"search_index={len(search_index)}")


if __name__ == "__main__":
    main()
