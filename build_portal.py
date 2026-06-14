"""統合ポータル（医知創造ラボ）の index.html を生成するスクリプト。

入力: corpus_cache.json（正準ブログデータ）と medical-ddx-tools/ の走査結果。
出力: portal/index.html（単一ファイル・CSS/JS内包・外部依存なし）。
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
    """カテゴリ1件分のカードHTMLを返す。"""
    safe = html_lib.escape(label)
    return (
        f'<a class="cat-card" href="{url}">'
        f'<span class="cat-name">{safe}</span>'
        f'<span class="cat-count">{count}</span></a>'
    )


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#15324E">
<meta name="description" content="{{tagline}}">
<title>{{brand}}｜医療と健康の知のハブ</title>
<style>
:root{--navy:#15324E;--navy2:#214E73;--blue:#2C6CA8;--coral:#E0744E;--coral-d:#B85733;--ink:#1B2A38;--muted:#5C6B78;--line:#E5EAF0;--bg:#F6F8FB;--card:#fff;--serif:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"MS PMincho",serif;--shadow:0 1px 2px rgba(21,50,78,.05),0 8px 26px rgba(21,50,78,.07)}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Yu Gothic","游ゴシック","Hiragino Kaku Gothic ProN","Segoe UI",sans-serif;color:var(--ink);background:var(--bg);line-height:1.7;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.wrap{max-width:1040px;margin:0 auto;padding:0 20px}
.hero{position:relative;color:#fff;background:linear-gradient(135deg,#122D47,#214E73 55%,#2C6CA8)}
.hero::after{content:"";position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.07) 1px,transparent 1px);background-size:22px 22px;opacity:.55;pointer-events:none}
.search{position:relative;max-width:560px;margin:26px auto 0;text-align:left;z-index:60}
.search input{width:100%;padding:14px 20px;border:0;border-radius:30px;font-size:16px;box-shadow:0 8px 28px rgba(0,0,0,.22);outline:none;color:#1B2A38;font-family:inherit}
.results{position:absolute;left:0;right:0;top:calc(100% + 8px);background:#fff;border-radius:14px;box-shadow:0 16px 44px rgba(21,50,78,.30);overflow:hidden;max-height:62vh;overflow-y:auto;z-index:60}
.results a{display:flex;align-items:center;gap:10px;padding:11px 16px;border-bottom:1px solid #eef2f6;color:#1B2A38;text-decoration:none;font-size:14px}
.results a:last-child{border-bottom:0}
.results a:hover{background:#F4F8FC}
.results .k{font-size:11px;font-weight:700;color:#fff;background:#2C6CA8;border-radius:10px;padding:2px 8px;white-space:nowrap;flex:none}
.results .ft{color:#2C6CA8;font-weight:700}
.results .empty{padding:14px 16px;color:#5C6B78;font-size:14px}
.hero-inner{position:relative;text-align:center;padding:66px 20px 54px}
.eyebrow{display:inline-block;font-size:12px;letter-spacing:.24em;color:#A6C8E6;font-weight:600}
.hero h1{font-family:var(--serif);font-size:46px;font-weight:600;letter-spacing:.07em;margin:14px 0 0;line-height:1.25}
.hero .tagline{margin:14px auto 0;font-size:16px;color:#D9E7F4;max-width:640px}
.rule{width:64px;height:3px;background:var(--coral);border-radius:2px;margin:24px auto 0}
.stats{display:flex;justify-content:center;margin:28px auto 0;flex-wrap:wrap}
.stat{padding:4px 28px;border-left:1px solid rgba(255,255,255,.18)}
.stat:first-child{border-left:0}
.stat-num{display:block;font-family:var(--serif);font-size:30px;font-weight:600;color:#fff;letter-spacing:.02em}
.stat-label{display:block;font-size:12px;color:#B7D2E8;margin-top:2px}
.cta{margin-top:32px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.cta a{padding:12px 24px;border-radius:8px;font-weight:600;font-size:15px;transition:.15s}
.cta .primary{background:var(--coral);color:#fff}
.cta .primary:hover{background:var(--coral-d)}
.cta .ghost{border:1px solid rgba(255,255,255,.5);color:#fff}
.cta .ghost:hover{background:rgba(255,255,255,.12)}
main{padding:58px 0 24px}
.section{margin-bottom:58px}
.sec-head{margin-bottom:22px}
.sec-eyebrow{font-size:12px;letter-spacing:.2em;color:var(--coral-d);font-weight:700;text-transform:uppercase}
.sec-head h2{font-size:24px;font-weight:700;color:var(--ink);margin-top:6px;letter-spacing:.02em}
.sec-head p{color:var(--muted);margin-top:6px;font-size:14px}
.cat-group{margin-top:22px}
.group-title{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:700;color:var(--ink);margin-bottom:13px}
.group-title::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--blue)}
.cat-group-0 .group-title::before{background:var(--navy)}
.cat-group-2 .group-title::before{background:var(--coral)}
.cat-grid{display:flex;flex-wrap:wrap;gap:10px}
.cat-card{display:inline-flex;align-items:center;gap:9px;background:var(--card);border:1px solid var(--line);border-radius:30px;padding:9px 8px 9px 17px;font-weight:600;font-size:14px;color:var(--ink);box-shadow:var(--shadow);transition:.15s}
.cat-card:hover{transform:translateY(-2px);border-color:var(--blue)}
.cat-count{font-size:12px;color:#fff;background:var(--blue);border-radius:20px;padding:2px 9px;font-weight:700}
.cat-group-0 .cat-count{background:var(--navy)}
.cat-group-2 .cat-count{background:var(--coral)}
.lead-card{display:block;background:linear-gradient(120deg,#1B3E5C,#2C6CA8);color:#fff;border-radius:16px;padding:28px 30px;box-shadow:var(--shadow);margin-bottom:18px;transition:.15s}
.lead-card:hover{transform:translateY(-2px)}
.lead-eyebrow{font-size:12px;letter-spacing:.16em;color:#A6C8E6;font-weight:700}
.lead-title{display:block;font-family:var(--serif);font-size:24px;font-weight:600;line-height:1.5;margin-top:8px}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--blue);border-radius:14px;padding:20px;box-shadow:var(--shadow);transition:.15s}
.card:hover{transform:translateY(-3px);border-left-color:var(--coral)}
.card .t{font-weight:700;color:var(--ink);line-height:1.55}
.big-links{display:flex;flex-wrap:wrap;gap:16px}
.big-links a{flex:1 1 240px;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--coral);border-radius:14px;padding:22px;box-shadow:var(--shadow);font-weight:700;color:var(--ink);transition:.15s}
.big-links a:hover{transform:translateY(-2px)}
.big-links a span{display:block;font-weight:400;color:var(--muted);font-size:13px;margin-top:6px}
.more{margin-top:16px;font-size:14px;font-weight:700;color:var(--blue)}
.more a{color:var(--blue)}
.about{background:#fff;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.about .wrap{padding:34px 20px;display:flex;gap:22px;align-items:center;flex-wrap:wrap}
.about .badge{font-family:var(--serif);font-size:13px;letter-spacing:.16em;color:var(--coral-d);font-weight:700;white-space:nowrap}
.about p{color:var(--muted);font-size:14px;flex:1 1 320px;line-height:1.8}
footer{background:#122D47;color:#cdddea;margin-top:30px}
footer .wrap{padding:36px 20px;text-align:center}
footer .fbrand{font-family:var(--serif);font-size:19px;color:#fff;letter-spacing:.1em}
footer nav{margin-top:14px}
footer nav a{margin:0 11px;color:#cdddea;font-size:14px}
footer nav a:hover{color:#fff}
footer .disc{margin-top:16px;font-size:12px;color:#88A4BA;line-height:1.7}
@media(max-width:720px){.hero h1{font-size:32px}.hero-inner{padding:48px 18px 42px}.stat{padding:4px 16px}.stat-num{font-size:22px}.sec-head h2{font-size:20px}.lead-title{font-size:20px}main{padding:44px 0 16px}.section{margin-bottom:46px}}
</style>
</head>
<body>
<header class="hero"><div class="hero-inner">
<span class="eyebrow">脳神経内科医が運営</span>
<h1>{{brand}}</h1>
<p class="tagline">{{tagline}}</p>
<div class="rule"></div>
<div class="search"><input id="q" type="search" autocomplete="off" placeholder="記事・ツール・動画を検索…" aria-label="サイト内検索"><div id="results" class="results" hidden></div></div>
<div class="stats">{{stats_html}}</div>
<div class="cta">
<a class="primary" href="#blog">記事を探す</a>
<a class="ghost" href="{{tools_url}}">診断ツール</a>
<a class="ghost" href="{{youtube_url}}">YouTube</a>
</div>
</div></header>
<main class="wrap">
<section class="section" id="supervisor">
<div class="sec-head"><span class="sec-eyebrow">監修者</span><h2>監修者からのコメント</h2></div>
<iframe id="supcmt" src="comment.html" title="監修者からのコメント" loading="lazy" scrolling="no" style="width:100%;border:0;display:block;overflow:hidden"></iframe>
</section>
<section class="section" id="blog">
<div class="sec-head"><span class="sec-eyebrow">Articles</span><h2>ブログ記事を探す</h2><p>読者・テーマ・シリーズから、目的の記事へ。</p></div>
{{category_groups_html}}
</section>
<section class="section" id="latest">
<div class="sec-head"><span class="sec-eyebrow">Latest</span><h2>最新の記事</h2><p>ブログの新着記事を自動で表示しています。</p></div>
<div id="latest-wrap">{{latest_html}}</div>
</section>
<section class="section" id="tools">
<div class="sec-head"><span class="sec-eyebrow">Tools</span><h2>診断ツール</h2><p>臨床の鑑別を支援するインタラクティブツール。</p></div>
{{tools_html}}
<div class="more"><a href="{{tools_url}}">すべてのツールを見る →</a></div>
</section>
<section class="section" id="check">
<div class="sec-head"><span class="sec-eyebrow">Self-check</span><h2>症状セルフチェック</h2><p>一般の方向け。気になる症状から調べられます。</p></div>
<div class="big-links"><a href="{{check_url}}">症状チェッカーを開く<span>気になる症状からセルフチェック</span></a></div>
</section>
<section class="section" id="visual">
<div class="sec-head"><span class="sec-eyebrow">Visuals</span><h2>インフォグラフィック・スライド</h2><p>要点を一枚で。図解とスライド資料。</p></div>
{{visual_html}}
</section>
<section class="section" id="youtube">
<div class="sec-head"><span class="sec-eyebrow">YouTube</span><h2>動画で学ぶ</h2><p>「{{brand}}」チャンネルで解説動画を配信中。</p></div>
<div class="big-links"><a href="{{youtube_url}}">チャンネルを見る<span>医療・健康の解説動画</span></a></div>
</section>
</main>
<section class="about"><div class="wrap">
<span class="badge">ABOUT</span>
<p>{{intro}}</p>
</div></section>
<footer><div class="wrap">
<div class="fbrand">{{brand}}</div>
<nav><a href="https://blog.ichisouzo-lab.com">ブログ</a><a href="{{tools_url}}">診断ツール</a><a href="{{check_url}}">症状チェック</a><a href="{{youtube_url}}">YouTube</a></nav>
<div class="disc">本サイトの情報は一般的な医療情報であり、個別の診断・治療に代わるものではありません。</div>
</div></footer>
<script>
(function(){var i=document.getElementById('q'),b=document.getElementById('results'),x=null,l=false,t;
var C={'記事':'#2C6CA8','ツール':'#15324E','図解':'#E0744E','スライド':'#2E7D62'};
function e(s){return (s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function ld(){if(x||l)return;l=true;fetch('search-index.json').then(function(res){return res.json();}).then(function(d){x=d;render(i.value);}).catch(function(){l=false;});}
function ft(q){return '<a class="ft" href="https://blog.ichisouzo-lab.com/search?q='+encodeURIComponent(q)+'">「'+e(q)+'」をブログ全文検索 →</a>';}
function render(q){q=(q||'').trim();if(!q){b.hidden=true;b.innerHTML='';return;}if(!x){b.hidden=false;b.innerHTML='<div class="empty">読み込み中…</div>';ld();return;}var n=q.toLowerCase(),h=[];for(var k=0;k<x.length&&h.length<20;k++){if((x[k].t||'').toLowerCase().indexOf(n)>=0)h.push(x[k]);}var o='';h.forEach(function(m){o+='<a href="'+m.u+'"><span class="k" style="background:'+(C[m.k]||'#2C6CA8')+'">'+m.k+'</span><span>'+e(m.t)+'</span></a>';});if(!h.length){o+='<div class="empty">該当する見出しがありません。全文検索をお試しください。</div>';}o+=ft(q);b.innerHTML=o;b.hidden=false;}
i.addEventListener('focus',ld);
i.addEventListener('input',function(){clearTimeout(t);t=setTimeout(function(){render(i.value);},120);});
i.addEventListener('keydown',function(ev){if(ev.key==='Enter'){var f=b.querySelector('a');if(f){window.location.href=f.getAttribute('href');}}});
document.addEventListener('click',function(ev){if(!ev.target.closest('.search')){b.hidden=true;}});})();
(function(){var w=document.getElementById('latest-wrap');if(!w)return;
function e(s){return (s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
fetch('https://blog.ichisouzo-lab.com/rss').then(function(r){return r.text();}).then(function(x){
var doc=new DOMParser().parseFromString(x,'application/xml');var it=doc.querySelectorAll('item');var a=[];
for(var k=0;k<it.length&&a.length<8;k++){var t=it[k].querySelector('title'),l=it[k].querySelector('link');if(t&&l&&l.textContent.trim()){a.push({t:t.textContent,u:l.textContent.trim()});}}
if(!a.length)return;
var h='<a class="lead-card" href="'+a[0].u+'"><span class="lead-eyebrow">最新の記事</span><span class="lead-title">'+e(a[0].t)+'</span></a>';
var c='';for(var j=1;j<a.length;j++){c+='<a class="card" href="'+a[j].u+'"><span class="t">'+e(a[j].t)+'</span></a>';}
if(c){h+='<div class="card-grid">'+c+'</div>';}w.innerHTML=h;
}).catch(function(){});})();
(function(){var f=document.getElementById('supcmt');if(!f)return;function fit(){try{var d=f.contentDocument;if(d&&d.documentElement){f.style.height=d.documentElement.scrollHeight+'px';}}catch(e){}}f.addEventListener('load',fit);setTimeout(fit,400);window.addEventListener('resize',fit);})();
</script>
</body>
</html>"""


def render_page(ctx):
    """コンテキスト辞書から完成HTMLを返す。未指定キーは空文字。"""
    keys = ["brand", "tagline", "intro", "stats_html", "youtube_url", "tools_url",
            "check_url", "category_groups_html", "latest_html", "tools_html", "visual_html"]
    out = PAGE_TEMPLATE
    for k in keys:
        out = out.replace("{{" + k + "}}", str(ctx.get(k, "")))
    return out


# ---- セクション組立 ---------------------------------------------------------

def build_stats_html(published, tools, slides, infographics):
    """ヒーローの統計セル（記事数・ツール数など）のHTMLを生成。"""
    items = [(f"{published:,}", "公開記事"), (str(tools), "診断ツール"),
             (str(slides), "スライド"), (str(infographics), "インフォグラフィック")]
    return "".join(
        f'<div class="stat"><span class="stat-num">{n}</span>'
        f'<span class="stat-label">{label}</span></div>'
        for n, label in items
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
    """設定のカテゴリグループからHTMLを生成。件数0のカテゴリはスキップ。"""
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
                f'<div class="cat-group cat-group-{i}">'
                f'<div class="group-title">{html_lib.escape(g["title"])}</div>'
                f'<div class="cat-grid">{"".join(cards)}</div></div>'
            )
    return "".join(parts)


def build_latest_html(articles):
    """最新記事のHTMLを生成。先頭1件を大きな「リード記事」、残りをカードグリッドで。"""
    if not articles:
        return ""
    lead = articles[0]
    lead_html = (
        f'<a class="lead-card" href="{lead.get("url", "")}">'
        f'<span class="lead-eyebrow">最新の記事</span>'
        f'<span class="lead-title">{html_lib.escape(lead.get("title", ""))}</span></a>'
    )
    cards = []
    for a in articles[1:]:
        t = html_lib.escape(a.get("title", ""))
        cards.append(f'<a class="card" href="{a.get("url", "")}"><span class="t">{t}</span></a>')
    grid = f'<div class="card-grid">{"".join(cards)}</div>' if cards else ""
    return lead_html + grid


def build_tools_html(tool_files, tools_url, featured, labels=None):
    """代表ツール（featured優先・無ければ先頭数件）のカードHTMLを生成。

    labels に日本語名があればそれ（絵文字付き）を表示し、無ければファイル名にフォールバック。
    """
    labels = labels or {}
    picks = [t for t in featured if t in tool_files] or tool_files[:6]
    cards = []
    for fn in picks:
        info = labels.get(fn)
        if info and info.get("name"):
            emoji = html_lib.escape(info.get("emoji", ""))
            name = html_lib.escape(info["name"])
            inner = f'{emoji} {name}'.strip()
        else:
            inner = html_lib.escape(fn.replace(".html", ""))
        cards.append(f'<a class="card" href="{tools_url}/{fn}"><span class="t">{inner}</span></a>')
    return f'<div class="card-grid">{"".join(cards)}</div>'


def build_subsite_cards(slugs, tools_url, sub, labels):
    """サブサイト（infographics/slides）のカードHTMLを生成。

    labels に日本語名があればそれを、無ければ slug を表示。リンクは {tools_url}/{sub}/{slug}/。
    """
    cards = []
    for slug in slugs:
        label = html_lib.escape(labels.get(slug) or slug)
        cards.append(f'<a class="card" href="{tools_url}/{sub}/{slug}/">'
                     f'<span class="t">{label}</span></a>')
    return f'<div class="card-grid">{"".join(cards)}</div>'


def build_visual_html(ig_slugs, ig_labels, slide_slugs, slide_labels, slide_total, tools_url,
                      gallery_count=0):
    """インフォグラフィック（全件）＋スライド（新着）の2サブグループHTMLを生成。"""
    ig_links = (f'<div class="more"><a href="{tools_url}/infographics/">'
                f'インフォグラフィック一覧を見る →</a></div>')
    if gallery_count:
        ig_links += (f'<div class="more"><a href="{tools_url}/infographics-gallery/">'
                     f'画像版インフォグラフィック集（{gallery_count}点）を見る →</a></div>')
    parts = [
        '<div class="cat-group"><div class="group-title">インフォグラフィック</div>',
        build_subsite_cards(ig_slugs, tools_url, "infographics", ig_labels),
        ig_links + '</div>',
        '<div class="cat-group" style="margin-top:30px"><div class="group-title">スライド資料（新着）</div>',
        build_subsite_cards(slide_slugs, tools_url, "slides", slide_labels),
        f'<div class="more"><a href="{tools_url}/slides/">'
        f'全スライド（{slide_total}本）を見る →</a></div></div>',
    ]
    return "".join(parts)


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

    ig_dir = tools_dir / "infographics"
    ig_slugs = scan_subsites(ig_dir)
    ig_labels = parse_subsite_labels(ig_dir)

    slide_dir = tools_dir / "slides"
    slide_recent = recent_subsites(slide_dir, config.get("slides_recent_count", 8))
    slide_labels = parse_subsite_labels(slide_dir)
    slide_all = scan_subsites(slide_dir)
    slide_total = len(slide_all)

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
        "stats_html": build_stats_html(len(pub), len(tool_files), slide_total, len(ig_slugs)),
        "youtube_url": config["youtube_url"],
        "tools_url": config["tools_url"],
        "check_url": config["check_url"],
        "category_groups_html": build_category_groups_html(
            config["category_groups"], counts, config["blog_base"]),
        "latest_html": build_latest_html(latest_articles(pub, config["latest_count"])),
        "tools_html": build_tools_html(tool_files, config["tools_url"],
                                       featured.get("featured_tools", []), tool_labels),
        "visual_html": build_visual_html(ig_slugs, ig_labels, slide_recent, slide_labels,
                                         slide_total, config["tools_url"], gallery_count),
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
