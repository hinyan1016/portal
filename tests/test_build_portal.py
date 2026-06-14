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
        "visual_html": "<div>visual</div>",
    }
    html = bp.render_page(ctx)
    for needle in ["医知創造ラボ", "ブログ", "診断ツール", "症状", "YouTube",
                   "<div>cats</div>", "<div>latest</div>", "<div>visual</div>"]:
        assert needle in html
    # 既知のプレースホルダトークンが未置換で残っていないこと
    # （CSSのネストした波括弧 }} を誤検出しないよう、トークン単位で検査する）
    for k in ["brand", "tagline", "youtube_url", "tools_url", "check_url",
              "category_groups_html", "latest_html", "tools_html", "visual_html"]:
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


# ---- インフォグラフィック/スライド日本語ラベル ----

def test_clean_page_title_strips_infographic_boilerplate():
    title = "細胞外液補充液の使い分け 早見インフォグラフィック｜生食 vs リンゲル液 ― 医知創造ラボ"
    assert bp.clean_page_title(title) == "細胞外液補充液の使い分け"


def test_clean_page_title_strips_slide_boilerplate():
    assert bp.clean_page_title("「自律神経失調症」と言われたら | スライド資料") == "「自律神経失調症」と言われたら"


def test_clean_page_title_empty_returns_none():
    assert bp.clean_page_title("") is None


def test_scan_subsites_excludes_underscore_dirs(tmp_path):
    (tmp_path / "_template").mkdir()
    (tmp_path / "_template" / "index.html").write_text("x", encoding="utf-8")
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "index.html").write_text("x", encoding="utf-8")
    assert bp.scan_subsites(tmp_path) == ["real"]


def test_parse_subsite_labels_reads_and_cleans_titles(tmp_path):
    d = tmp_path / "extracellular-fluid"
    d.mkdir()
    (d / "index.html").write_text(
        "<title>細胞外液補充液の使い分け 早見インフォグラフィック｜x ― 医知創造ラボ</title>",
        encoding="utf-8")
    labels = bp.parse_subsite_labels(tmp_path)
    assert labels["extracellular-fluid"] == "細胞外液補充液の使い分け"


def test_recent_subsites_orders_by_mtime_desc(tmp_path):
    import os
    for name, t in [("old", 1000000000), ("new", 2000000000), ("_tmpl", 3000000000)]:
        d = tmp_path / name
        d.mkdir()
        f = d / "index.html"
        f.write_text("x", encoding="utf-8")
        os.utime(f, (t, t))
    assert bp.recent_subsites(tmp_path, 5) == ["new", "old"]  # _tmpl除外・mtime降順


def test_build_subsite_cards_uses_labels_and_path():
    html = bp.build_subsite_cards(["cns-sjogren"], "https://t", "infographics",
                                  {"cns-sjogren": "中枢神経系シェーグレン症候群"})
    assert "中枢神経系シェーグレン症候群" in html
    assert 'href="https://t/infographics/cns-sjogren/"' in html


def test_build_subsite_cards_falls_back_to_slug():
    html = bp.build_subsite_cards(["foo"], "https://t", "slides", {})
    assert "foo" in html
    assert 'href="https://t/slides/foo/"' in html


def test_build_search_index_covers_all_kinds():
    pub = [{"title": "記事A", "url": "https://blog.x/entry/a", "draft": "no"}]
    idx = bp.build_search_index(
        pub, ["aki.html"], {"aki.html": {"name": "AKIツール", "emoji": "🫘"}},
        ["cns"], {"cns": "図1"}, ["sl"], {"sl": "スライド1"}, "https://t")
    kinds = {i["k"] for i in idx}
    assert kinds == {"記事", "ツール", "図解", "スライド"}
    by = {i["t"]: i for i in idx}
    assert by["記事A"]["u"] == "https://blog.x/entry/a"
    assert by["AKIツール"]["u"] == "https://t/aki.html"
    assert by["図1"]["u"] == "https://t/infographics/cns/"
    assert by["スライド1"]["u"] == "https://t/slides/sl/"


def test_build_search_index_falls_back_to_filename_or_slug():
    idx = bp.build_search_index([], ["foo.html"], {}, ["bar"], {}, [], {}, "https://t")
    titles = {i["t"] for i in idx}
    assert "foo" in titles and "bar" in titles


def test_build_stats_html_formats_thousands():
    html = bp.build_stats_html(1051, 40, 83, 10)
    assert "1,051" in html and "公開記事" in html
    assert "40" in html and "診断ツール" in html
    assert "83" in html and "10" in html


def test_build_visual_html_has_both_groups_and_total_link():
    html = bp.build_visual_html(["ig1"], {"ig1": "図1"}, ["sl1"], {"sl1": "スライド1"}, 83, "https://t")
    assert "インフォグラフィック" in html and "スライド資料" in html
    assert "図1" in html and "スライド1" in html
    assert "83" in html
    assert 'href="https://t/infographics/"' in html
    assert 'href="https://t/slides/"' in html
