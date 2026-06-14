from urllib.parse import unquote

import build_portal as bp


SAMPLE = [
    {"url": "https://blog.ichisouzo-lab.com/entry/a", "title": "A",
     "categories": ["脳神経内科", "医師向け"], "published": "2026-01-01T00:00:00+09:00", "draft": "no"},
    {"url": "https://blog.ichisouzo-lab.com/entry/b", "title": "B",
     "categories": ["脳神経内科"], "published": "2026-02-01T00:00:00+09:00", "draft": "no"},
    {"url": "https://blog.ichisouzo-lab.com/entry/c", "title": "C(下書き)",
     "categories": ["薬"], "published": "2026-03-01T00:00:00+09:00", "draft": "yes"},
]


# ---- Task 2 ----

def test_published_records_excludes_drafts():
    pub = bp.published_records(SAMPLE)
    assert len(pub) == 2
    assert all(r["draft"] != "yes" for r in pub)


def test_count_categories_counts_only_published():
    counts = bp.count_categories(bp.published_records(SAMPLE))
    assert counts["脳神経内科"] == 2
    assert counts["医師向け"] == 1
    assert "薬" not in counts  # 下書きのみなので0


# ---- Task 3 ----

def test_hatena_category_url_encodes_japanese():
    base = "https://blog.ichisouzo-lab.com"
    url = bp.hatena_category_url(base, "脳神経内科")
    assert url.startswith(base + "/archive/category/")
    encoded = url.split("/archive/category/")[1]
    assert unquote(encoded) == "脳神経内科"
    assert "脳" not in url  # 生の日本語が混ざっていない（=エンコード済み）


# ---- Task 4 ----

def test_latest_articles_sorted_desc_and_limited():
    latest = bp.latest_articles(bp.published_records(SAMPLE), 1)
    assert len(latest) == 1
    assert latest[0]["title"] == "B"  # 公開のうち published が最新


def test_latest_articles_excludes_drafts():
    latest = bp.latest_articles(SAMPLE, 10)
    titles = [a["title"] for a in latest]
    assert "C(下書き)" not in titles


# ---- Task 5 ----

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


# ---- Task 6 ----

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
    for needle in ["医知創造ラボ", "ブログ", "診断ツール", "症状", "YouTube",
                   "<div>cats</div>", "<div>latest</div>"]:
        assert needle in html
    # 既知のプレースホルダトークンが未置換で残っていないこと
    # （CSSのネストした波括弧 }} を誤検出しないよう、トークン単位で検査する）
    for k in ["brand", "tagline", "youtube_url", "tools_url", "check_url",
              "category_groups_html", "latest_html", "tools_html", "infographics_html"]:
        assert "{{" + k + "}}" not in html
    assert html.lstrip().startswith("<!DOCTYPE html>")


# ---- Task 7 ----

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


# ---- ツール日本語ラベル ----

def test_parse_tool_labels_extracts_name_and_emoji(tmp_path):
    idx = tmp_path / "index.html"
    idx.write_text(
        '<a class="tool-card" href="aki.html">\n'
        '  <div class="tool-emoji">🫘</div>\n'
        '  <div class="tool-name">急性腎障害（AKI）鑑別診断ツール</div>\n'
        '  <div class="tool-desc">説明</div>\n</a>',
        encoding="utf-8")
    labels = bp.parse_tool_labels(idx)
    assert labels["aki.html"]["name"] == "急性腎障害（AKI）鑑別診断ツール"
    assert labels["aki.html"]["emoji"] == "🫘"


def test_build_tools_html_uses_japanese_label_when_available():
    labels = {"hyponatremia.html": {"name": "低ナトリウム血症 鑑別診断ツール", "emoji": "🧪"}}
    html = bp.build_tools_html(["hyponatremia.html"], "https://t",
                              ["hyponatremia.html"], labels)
    assert "低ナトリウム血症 鑑別診断ツール" in html
    assert "🧪" in html
    assert 'href="https://t/hyponatremia.html"' in html


def test_build_tools_html_falls_back_to_filename_without_label():
    html = bp.build_tools_html(["foo.html"], "https://t", ["foo.html"], {})
    assert "foo" in html
