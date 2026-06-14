# 統合ポータル（医知創造ラボ）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** apex `ichisouzo-lab.com` に置く「医知創造ラボ」統合ポータルの単一 `index.html` を、`corpus_cache.json` と `medical-ddx-tools/` から自動生成するスクリプトと共に作る。

**Architecture:** Python 生成スクリプト `build_portal.py` が純関数群（データ読込・カテゴリ集計・URL生成・最新記事抽出・ツール走査・HTML描画）を組み合わせて `index.html` を丸ごと出力する。ロジックは pytest で TDD。HTML は外部依存なしの単一ファイル（CSS/JS 内包）。DNS 切替は本計画のスコープ外（最終工程・別途）。

**Tech Stack:** Python 3.13（`/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe`）、pytest 8.3.4、標準ライブラリのみ（json, csv不要, urllib.parse, pathlib, html）。出力は静的 HTML/CSS/JS。

---

## 前提・パス

- 作業ルート（ワークスペース）: `C:\Users\jsber\OneDrive\Documents\Claude_task_new`（git管理しない）
- ポータルリポジトリ: `portal/`（git初期化済み・独立リポ）
- 正準データ: `medical-content/blog/seo-improvement/corpus_cache.json`（list[record], 約1051件）
- ツール群: `medical-ddx-tools/`（root直下 `*.html` がツール、`infographics/<slug>/`、`slides/<slug>/`）
- Python 実行（Git Bash）: `PY=/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe`
- テスト実行: `$PY -m pytest portal/tests -q`
- **Windows/OneDrive 注意**: ファイル書込は LF 明示（`newline="\n"`）。`portal/` の git は `windows.appendAtomically false` 設定済み。

## File Structure

| ファイル | 責務 |
|---|---|
| `portal/config.json` | ブランド名・サブドメインURL・YouTube URL・カテゴリ選定（3グループ）・最新記事件数・各入力パス |
| `portal/featured.json` | 手動の注目記事（URL/タイトル）・代表ツール（slug）の上書きリスト |
| `portal/build_portal.py` | 純関数群＋`main()`。`index.html` を生成 |
| `portal/index.html` | 生成物（コミット対象） |
| `portal/tests/test_build_portal.py` | pytest ユニットテスト |
| `portal/README.md` | 使い方（再生成手順） |
| `portal/.gitignore` | `__pycache__/`, `*.pyc` |

> `build_portal.py` は1ファイルだが関数で責務分割（読込/集計/URL/最新/走査/描画/組立）。描画は「セクションごとの関数」に分け、`render_page()` が組み立てる。

---

### Task 1: スキャフォールド（設定・固定ファイル）

**Files:**
- Create: `portal/.gitignore`
- Create: `portal/config.json`
- Create: `portal/featured.json`
- Create: `portal/tests/__init__.py`（空）

- [ ] **Step 1: `.gitignore` を作成**

```
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 2: `config.json` を作成**

```json
{
  "brand": "医知創造ラボ",
  "tagline": "脳神経内科医がつくる、医療と健康のための知のハブ",
  "apex_url": "https://ichisouzo-lab.com",
  "blog_base": "https://blog.ichisouzo-lab.com",
  "tools_url": "https://tools.ichisouzo-lab.com",
  "check_url": "https://check.ichisouzo-lab.com",
  "youtube_url": "https://www.youtube.com/@ichisouzo-lab",
  "corpus_path": "medical-content/blog/seo-improvement/corpus_cache.json",
  "tools_dir": "medical-ddx-tools",
  "latest_count": 8,
  "category_groups": [
    {"title": "読者別に探す", "categories": ["医師向け", "初期研修医", "一般向け"]},
    {"title": "テーマで探す", "categories": ["脳神経内科", "薬", "医療安全", "てんかん", "脳卒中", "感染症", "栄養", "認知症", "糖尿", "頭痛", "パーキンソン病", "ガイドライン"]},
    {"title": "シリーズで読む", "categories": ["その症状大丈夫", "からだの不思議", "20年の変遷シリーズ", "セルフチェック"]}
  ]
}
```

- [ ] **Step 3: `featured.json` を作成**（初期は空配列。生成後に手動で埋める）

```json
{
  "featured_articles": [],
  "featured_tools": ["hyponatremia.html", "headache.html", "secondary_hypertension.html"]
}
```

- [ ] **Step 4: テストパッケージinitを作成**

`portal/tests/__init__.py` は空ファイル。

- [ ] **Step 5: コミット**

```bash
cd portal && git add .gitignore config.json featured.json tests/__init__.py && \
git -c user.name="hinyan1016" -c user.email="hinyan1016@gmail.com" commit -q -m "chore: ポータルのスキャフォールド（設定・固定ファイル）"
```

---

### Task 2: データ読込とカテゴリ集計

**Files:**
- Create: `portal/build_portal.py`
- Test: `portal/tests/test_build_portal.py`

- [ ] **Step 1: 失敗するテストを書く**

`portal/tests/test_build_portal.py`:

```python
import build_portal as bp


SAMPLE = [
    {"url": "https://blog.ichisouzo-lab.com/entry/a", "title": "A",
     "categories": ["脳神経内科", "医師向け"], "published": "2026-01-01T00:00:00+09:00", "draft": "no"},
    {"url": "https://blog.ichisouzo-lab.com/entry/b", "title": "B",
     "categories": ["脳神経内科"], "published": "2026-02-01T00:00:00+09:00", "draft": "no"},
    {"url": "https://blog.ichisouzo-lab.com/entry/c", "title": "C(下書き)",
     "categories": ["薬"], "published": "2026-03-01T00:00:00+09:00", "draft": "yes"},
]


def test_published_records_excludes_drafts():
    pub = bp.published_records(SAMPLE)
    assert len(pub) == 2
    assert all(r["draft"] != "yes" for r in pub)


def test_count_categories_counts_only_published():
    counts = bp.count_categories(bp.published_records(SAMPLE))
    assert counts["脳神経内科"] == 2
    assert counts["医師向け"] == 1
    assert "薬" not in counts  # 下書きのみなので0
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: FAIL（`AttributeError: module 'build_portal' has no attribute 'published_records'`）

- [ ] **Step 3: 最小実装**

`portal/build_portal.py`:

```python
"""統合ポータル（医知創造ラボ）の index.html を生成するスクリプト。

入力: corpus_cache.json（正準ブログデータ）と medical-ddx-tools/ の走査結果。
出力: portal/index.html（単一ファイル・CSS/JS内包・外部依存なし）。
"""
import json
from collections import Counter
from pathlib import Path


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
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: PASS（2 passed）

- [ ] **Step 5: コミット**

```bash
cd portal && git add build_portal.py tests/test_build_portal.py && \
git -c user.name="hinyan1016" -c user.email="hinyan1016@gmail.com" commit -q -m "feat: corpus読込とカテゴリ集計（TDD）"
```

---

### Task 3: はてなカテゴリURL生成（URLエンコード）

**Files:**
- Modify: `portal/build_portal.py`
- Test: `portal/tests/test_build_portal.py`

- [ ] **Step 1: 失敗するテストを追記**

`portal/tests/test_build_portal.py` の末尾に追記:

```python
from urllib.parse import unquote


def test_hatena_category_url_encodes_japanese():
    base = "https://blog.ichisouzo-lab.com"
    url = bp.hatena_category_url(base, "脳神経内科")
    assert url.startswith(base + "/archive/category/")
    # エンコード後でも、デコードすれば元のカテゴリ名に戻る
    encoded = url.split("/archive/category/")[1]
    assert unquote(encoded) == "脳神経内科"
    assert "脳" not in url  # 生の日本語が混ざっていない（=エンコード済み）
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: FAIL（`has no attribute 'hatena_category_url'`）

- [ ] **Step 3: 最小実装**（`build_portal.py` の import に `quote` を追加し関数を追記）

import 行を以下に変更:

```python
from urllib.parse import quote
```

関数を追記:

```python
def hatena_category_url(blog_base, category):
    """はてなの自動カテゴリページURLを返す（カテゴリ名はURLエンコード）。"""
    return f"{blog_base}/archive/category/{quote(category)}"
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: PASS（3 passed）

- [ ] **Step 5: コミット**

```bash
cd portal && git add build_portal.py tests/test_build_portal.py && \
git -c user.name="hinyan1016" -c user.email="hinyan1016@gmail.com" commit -q -m "feat: はてなカテゴリURL生成（URLエンコード・TDD）"
```

---

### Task 4: 最新記事の抽出

**Files:**
- Modify: `portal/build_portal.py`
- Test: `portal/tests/test_build_portal.py`

- [ ] **Step 1: 失敗するテストを追記**

```python
def test_latest_articles_sorted_desc_and_limited():
    latest = bp.latest_articles(bp.published_records(SAMPLE), 1)
    assert len(latest) == 1
    assert latest[0]["title"] == "B"  # 公開のうち published が最新

def test_latest_articles_excludes_drafts():
    latest = bp.latest_articles(SAMPLE, 10)
    titles = [a["title"] for a in latest]
    assert "C(下書き)" not in titles
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: FAIL（`has no attribute 'latest_articles'`）

- [ ] **Step 3: 最小実装**（追記）

```python
def latest_articles(records, n):
    """公開レコードを published 降順に並べ、先頭 n 件を返す。"""
    pub = published_records(records)
    pub.sort(key=lambda r: r.get("published", ""), reverse=True)
    return pub[:n]
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: PASS（5 passed）

- [ ] **Step 5: コミット**

```bash
cd portal && git add build_portal.py tests/test_build_portal.py && \
git -c user.name="hinyan1016" -c user.email="hinyan1016@gmail.com" commit -q -m "feat: 最新記事の抽出（TDD）"
```

---

### Task 5: ツール／インフォ／スライドの走査

**Files:**
- Modify: `portal/build_portal.py`
- Test: `portal/tests/test_build_portal.py`

- [ ] **Step 1: 失敗するテストを追記**

```python
def test_scan_tools_lists_root_html_excluding_index(tmp_path):
    (tmp_path / "aki.html").write_text("x", encoding="utf-8")
    (tmp_path / "headache.html").write_text("x", encoding="utf-8")
    (tmp_path / "index.html").write_text("x", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    tools = bp.scan_tools(tmp_path)
    assert tools == ["aki.html", "headache.html"]  # index.html除外・ソート済


def test_scan_subsites_lists_dirs_with_index(tmp_path):
    (tmp_path / "ino").mkdir()
    (tmp_path / "ino" / "index.html").write_text("x", encoding="utf-8")
    (tmp_path / "empty").mkdir()  # index.htmlなし→除外
    subs = bp.scan_subsites(tmp_path)
    assert subs == ["ino"]
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: FAIL（`has no attribute 'scan_tools'`）

- [ ] **Step 3: 最小実装**（追記）

```python
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
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: PASS（7 passed）

- [ ] **Step 5: コミット**

```bash
cd portal && git add build_portal.py tests/test_build_portal.py && \
git -c user.name="hinyan1016" -c user.email="hinyan1016@gmail.com" commit -q -m "feat: ツール/インフォ/スライド走査（TDD）"
```

---

### Task 6: HTML描画（カテゴリカード＋ページ組立）

**Files:**
- Modify: `portal/build_portal.py`
- Test: `portal/tests/test_build_portal.py`

- [ ] **Step 1: 失敗するテストを追記**

```python
def test_render_category_card_contains_label_count_url():
    html = bp.render_category_card("脳神経内科", 407, "https://x/archive/category/y")
    assert "脳神経内科" in html
    assert "407" in html
    assert 'href="https://x/archive/category/y"' in html


def test_render_page_has_all_sections_and_no_placeholders():
    ctx = {
        "brand": "医知創造ラボ", "tagline": "テスト",
        "youtube_url": "https://www.youtube.com/@ichisouzo-lab",
        "tools_url": "https://tools.ichisouzo-lab.com",
        "check_url": "https://check.ichisouzo-lab.com",
        "category_groups_html": "<div>cats</div>",
        "latest_html": "<div>latest</div>",
        "tools_html": "<div>tools</div>",
        "infographics_html": "<div>ig</div>",
    }
    html = bp.render_page(ctx)
    # 主要セクションが含まれる
    for needle in ["医知創造ラボ", "ブログ", "診断ツール", "症状", "YouTube",
                   "<div>cats</div>", "<div>latest</div>"]:
        assert needle in html
    # 未置換プレースホルダが残っていない
    assert "{{" not in html and "}}" not in html
    # 正しいHTML文書である
    assert html.lstrip().startswith("<!DOCTYPE html>")
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: FAIL（`has no attribute 'render_category_card'`）

- [ ] **Step 3: 最小実装**（`build_portal.py` に追記。`html` を import）

import 部に追加:

```python
import html as html_lib
```

カードとページ描画を追記:

```python
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
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: PASS（9 passed）

- [ ] **Step 5: コミット**

```bash
cd portal && git add build_portal.py tests/test_build_portal.py && \
git -c user.name="hinyan1016" -c user.email="hinyan1016@gmail.com" commit -q -m "feat: HTML描画（カテゴリカード・ページテンプレート・TDD）"
```

---

### Task 7: セクション組立と `main()`（実生成）

**Files:**
- Modify: `portal/build_portal.py`
- Test: `portal/tests/test_build_portal.py`

- [ ] **Step 1: 失敗するテストを追記**（セクションHTMLビルダのテスト）

```python
def test_build_category_groups_html_uses_config_groups():
    counts = {"脳神経内科": 407, "薬": 219}
    groups = [{"title": "テーマで探す", "categories": ["脳神経内科", "薬", "存在しない"]}]
    html = bp.build_category_groups_html(groups, counts, "https://blog.ichisouzo-lab.com")
    assert "テーマで探す" in html
    assert "脳神経内科" in html and "407" in html
    assert "存在しない" not in html  # 件数0のカテゴリはスキップ


def test_build_latest_html_links_titles():
    arts = [{"url": "https://blog.ichisouzo-lab.com/entry/a", "title": "記事A"}]
    html = bp.build_latest_html(arts)
    assert "記事A" in html
    assert 'href="https://blog.ichisouzo-lab.com/entry/a"' in html
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: FAIL（`has no attribute 'build_category_groups_html'`）

- [ ] **Step 3: 最小実装**（追記。セクションビルダ＋main）

```python
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
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q`
Expected: PASS（11 passed）

- [ ] **Step 5: 実データで生成**

Run: `cd portal && /c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe build_portal.py`
Expected: `Wrote .../index.html (...) ; published=1051, tools=..., infographics=...`（published が約1051）

- [ ] **Step 6: 生成物の健全性チェック**

Run: `cd portal && grep -c "cat-card" index.html && ! grep -q "{{" index.html && echo "no-placeholder-OK"`
Expected: cat-card が複数件、`no-placeholder-OK` が出力（未置換 `{{` が無い）

- [ ] **Step 7: コミット**

```bash
cd portal && git add build_portal.py tests/test_build_portal.py index.html && \
git -c user.name="hinyan1016" -c user.email="hinyan1016@gmail.com" commit -q -m "feat: セクション組立とmain・index.html生成（TDD）"
```

---

### Task 8: ブラウザ視覚検証（preview）と README

**Files:**
- Create: `portal/README.md`

- [ ] **Step 1: README を作成**

```markdown
# 統合ポータル（医知創造ラボ）

apex `ichisouzo-lab.com` 用のポータル `index.html` を生成する。

## 再生成
\`\`\`bash
/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe build_portal.py
\`\`\`
- データ源: `../medical-content/blog/seo-improvement/corpus_cache.json`
- ツール走査: `../medical-ddx-tools/`
- 手動調整: `featured.json`（注目記事・代表ツール）、`config.json`（カテゴリ選定・各URL）

## テスト
\`\`\`bash
/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q
\`\`\`

## デプロイ（最終工程・別途）
spec の §7 参照。完成後に `CNAME = ichisouzo-lab.com` を追加し、Cloudflare で
apex リダイレクト無効化＋Aレコード差し替えを行う。**ビルド段階では CNAME を置かない**。
```

- [ ] **Step 2: ローカルでブラウザ視覚確認**

`portal/index.html` をブラウザ（Claude in Chrome の navigate で `file:///C:/Users/jsber/OneDrive/Documents/Claude_task_new/portal/index.html`）で開き、スクリーンショットで確認。
チェック: ヒーロー表示／カテゴリカードに件数バッジ／各セクション見出し／スマホ幅（resize 380px）で1カラム。
問題があれば `build_portal.py` のCSS/テンプレートを修正し、再生成（Task7 Step5）→再確認。

- [ ] **Step 3: カテゴリリンクの実在確認（サンプル）**

Run: 生成された `index.html` から最初の `cat-card` の href を1つ取り出し、`curl -s -o /dev/null -w "%{http_code}" <URL>` で 200 を確認（はてなカテゴリページが存在すること）。
Expected: `200`

- [ ] **Step 4: コミット**

```bash
cd portal && git add README.md && \
git -c user.name="hinyan1016" -c user.email="hinyan1016@gmail.com" commit -q -m "docs: ポータルREADME＋視覚検証"
```

---

## スコープ外（本計画では実施しない）

- **GitHub リポジトリ作成・push・Pages 有効化**：ユーザー確認のうえ後続で実施。
- **DNS 切替（Cloudflare）**：spec §7。apex リダイレクト無効化＋Aレコード差し替え＋www追加＋CNAMEファイル。ポータル完成・確認後にユーザー判断で実施。
- **featured_articles の内容選定**：生成後にユーザーと相談して `featured.json` を充実。
- **ブログ記事側からの相互リンク**：任意・後日。

---

## Self-Review（記入済み）

- **Spec coverage**: §3構成→Task6/7、§4生成方式→Task2-7、§5デプロイ（CNAME無し方針）→Task8 README/スコープ外、§6検証→Task8、§7 DNS→スコープ外に明記。全カバー。
- **Placeholder scan**: 各コードステップに実コードあり。TODO/TBD無し。
- **Type consistency**: 関数名 `published_records`/`count_categories`/`hatena_category_url`/`latest_articles`/`scan_tools`/`scan_subsites`/`render_category_card`/`render_page`/`build_category_groups_html`/`build_latest_html`/`build_tools_html`/`build_infographics_html`/`main` は定義と利用で一致。`render_page` のキーは Task6 テンプレートと Task7 ctx で一致。
