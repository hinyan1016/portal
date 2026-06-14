"""統合ポータル（医知創造ラボ）の index.html を生成するスクリプト。

入力: corpus_cache.json（正準ブログデータ）と medical-ddx-tools/ の走査結果。
出力: portal/index.html（単一ファイル・CSS/JS内包・外部依存なし）。
"""
import html as html_lib
import json
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


def scan_subsites(parent_dir):
    """親ディレクトリ直下で index.html を含むサブフォルダ名（slug）をソートして返す。"""
    p = Path(parent_dir)
    if not p.is_dir():
        return []
    return sorted(d.name for d in p.iterdir() if d.is_dir() and (d / "index.html").exists())


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
<meta name="theme-color" content="#1B3A5C">
<title>{{brand}}｜医療と健康の知のハブ</title>
<style>
:root{--navy:#1B3A5C;--blue:#2C5AA0;--light:#E8F0FE;--coral:#FF7A59;--shadow:0 2px 12px rgba(27,58,92,.12);--radius:12px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:"游ゴシック","Yu Gothic","Segoe UI",sans-serif;background:linear-gradient(135deg,#E8F0FE 0%,#F4F6F8 100%);color:#222;min-height:100vh;padding-bottom:60px;}
header{background:linear-gradient(135deg,var(--navy),var(--blue));color:#fff;padding:48px 20px 40px;text-align:center;}
header h1{font-size:2em;letter-spacing:.04em;}
header p{margin-top:10px;opacity:.9;}
.hero-links{margin-top:22px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap;}
.hero-links a{background:rgba(255,255,255,.15);color:#fff;text-decoration:none;padding:10px 18px;border-radius:24px;font-weight:600;border:1px solid rgba(255,255,255,.3);}
.hero-links a.primary{background:var(--coral);border-color:var(--coral);}
.container{max-width:960px;margin:0 auto;padding:32px 16px;}
section{margin-bottom:44px;}
section h2{font-size:1.35em;color:var(--navy);border-left:5px solid var(--coral);padding-left:12px;margin-bottom:18px;}
.group-title{font-size:1em;color:var(--blue);font-weight:700;margin:18px 0 10px;}
.cat-grid{display:flex;flex-wrap:wrap;gap:10px;}
.cat-card{display:flex;align-items:center;gap:8px;background:#fff;border-radius:24px;box-shadow:var(--shadow);padding:9px 16px;text-decoration:none;color:var(--navy);font-weight:600;border-left:4px solid var(--blue);transition:transform .15s;}
.cat-card:hover{transform:translateY(-2px);border-left-color:var(--coral);}
.cat-count{font-size:.8em;color:#fff;background:var(--blue);border-radius:12px;padding:1px 9px;}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px;}
.card{background:#fff;border-radius:var(--radius);box-shadow:var(--shadow);padding:20px;text-decoration:none;color:#222;border-left:5px solid var(--blue);transition:transform .15s;}
.card:hover{transform:translateY(-3px);border-left-color:var(--coral);}
.card .t{font-weight:700;color:var(--navy);line-height:1.5;}
.big-links{display:flex;flex-wrap:wrap;gap:14px;}
.big-links a{flex:1 1 220px;background:#fff;border-radius:var(--radius);box-shadow:var(--shadow);padding:22px;text-decoration:none;color:var(--navy);font-weight:700;border-left:5px solid var(--coral);}
.big-links a span{display:block;font-weight:400;color:#555;font-size:.85em;margin-top:6px;}
footer{max-width:960px;margin:20px auto 0;padding:24px 16px;border-top:1px solid #d8dee6;color:#777;font-size:.82em;text-align:center;}
footer a{color:var(--blue);text-decoration:none;margin:0 8px;}
@media(max-width:720px){.container{padding:20px 12px;}header h1{font-size:1.6em;}}
</style>
</head>
<body>
<header>
<h1>{{brand}}</h1>
<p>{{tagline}}</p>
<div class="hero-links">
<a class="primary" href="#blog">記事を探す</a>
<a href="{{tools_url}}">診断ツール</a>
<a href="{{youtube_url}}">YouTube</a>
</div>
</header>
<div class="container">
<section id="blog"><h2>ブログ記事を探す</h2>{{category_groups_html}}</section>
<section id="latest"><h2>注目・最新の記事</h2>{{latest_html}}</section>
<section id="tools"><h2>診断ツール</h2>{{tools_html}}
<p style="margin-top:14px"><a href="{{tools_url}}">▶ 全ツール一覧を見る</a></p></section>
<section id="check"><h2>症状セルフチェック（一般の方向け）</h2>
<div class="big-links"><a href="{{check_url}}">症状チェッカーを開く<span>気になる症状からセルフチェック</span></a></div></section>
<section id="visual"><h2>インフォグラフィック・スライド</h2>{{infographics_html}}</section>
<section id="youtube"><h2>YouTube「{{brand}}」</h2>
<div class="big-links"><a href="{{youtube_url}}">チャンネルを見る<span>医療・健康の解説動画</span></a></div></section>
</div>
<footer>
<div>{{brand}}</div>
<div style="margin-top:8px">
<a href="https://blog.ichisouzo-lab.com">ブログ</a>
<a href="{{tools_url}}">診断ツール</a>
<a href="{{check_url}}">症状チェック</a>
<a href="{{youtube_url}}">YouTube</a>
</div>
<div style="margin-top:12px;font-size:.95em">本サイトの情報は一般的な医療情報であり、個別の診断・治療に代わるものではありません。</div>
</footer>
</body>
</html>"""


def render_page(ctx):
    """コンテキスト辞書から完成HTMLを返す。未指定キーは空文字。"""
    keys = ["brand", "tagline", "youtube_url", "tools_url", "check_url",
            "category_groups_html", "latest_html", "tools_html", "infographics_html"]
    out = PAGE_TEMPLATE
    for k in keys:
        out = out.replace("{{" + k + "}}", str(ctx.get(k, "")))
    return out


# ---- セクション組立 ---------------------------------------------------------

def build_category_groups_html(groups, counts, blog_base):
    """設定のカテゴリグループからHTMLを生成。件数0のカテゴリはスキップ。"""
    parts = []
    for g in groups:
        cards = []
        for cat in g["categories"]:
            n = counts.get(cat, 0)
            if n <= 0:
                continue
            cards.append(render_category_card(cat, n, hatena_category_url(blog_base, cat)))
        if cards:
            parts.append(f'<div class="group-title">{html_lib.escape(g["title"])}</div>'
                         f'<div class="cat-grid">{"".join(cards)}</div>')
    return "".join(parts)


def build_latest_html(articles):
    """最新記事のカードHTMLを生成。"""
    cards = []
    for a in articles:
        t = html_lib.escape(a.get("title", ""))
        cards.append(f'<a class="card" href="{a.get("url", "")}"><span class="t">{t}</span></a>')
    return f'<div class="card-grid">{"".join(cards)}</div>'


def build_tools_html(tool_files, tools_url, featured):
    """代表ツール（featured優先・無ければ先頭数件）のカードHTMLを生成。"""
    picks = [t for t in featured if t in tool_files] or tool_files[:6]
    cards = []
    for fn in picks:
        label = html_lib.escape(fn.replace(".html", ""))
        cards.append(f'<a class="card" href="{tools_url}/{fn}"><span class="t">{label}</span></a>')
    return f'<div class="card-grid">{"".join(cards)}</div>'


def build_infographics_html(slugs, tools_url):
    """インフォグラフィック一覧へのカードHTMLを生成。"""
    cards = []
    for slug in slugs:
        label = html_lib.escape(slug)
        cards.append(f'<a class="card" href="{tools_url}/infographics/{slug}/">'
                     f'<span class="t">{label}</span></a>')
    return f'<div class="card-grid">{"".join(cards)}</div>'


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
    ig_slugs = scan_subsites(tools_dir / "infographics")

    ctx = {
        "brand": config["brand"],
        "tagline": config["tagline"],
        "youtube_url": config["youtube_url"],
        "tools_url": config["tools_url"],
        "check_url": config["check_url"],
        "category_groups_html": build_category_groups_html(
            config["category_groups"], counts, config["blog_base"]),
        "latest_html": build_latest_html(latest_articles(pub, config["latest_count"])),
        "tools_html": build_tools_html(tool_files, config["tools_url"],
                                       featured.get("featured_tools", [])),
        "infographics_html": build_infographics_html(ig_slugs, config["tools_url"]),
    }
    out = render_page(ctx)
    (here / "index.html").write_text(out, encoding="utf-8", newline="\n")
    print(f"Wrote {here / 'index.html'} ({len(out)} bytes); "
          f"published={len(pub)}, tools={len(tool_files)}, infographics={len(ig_slugs)}")


if __name__ == "__main__":
    main()
