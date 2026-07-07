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


# ---- 最新記事の読者別分割 ----

def test_is_general_reader_pro_title_marker_overrides_tag():
    # 「一般向け」タグが誤付与されていても、タイトルの専門家向けマーカーが優先される
    rec = {"title": "認知症予防の生活指導テンプレート【脳神経内科医向け】",
           "categories": ["医学情報", "一般向け"]}
    assert bp.is_general_reader(rec) is False
    for t in ["○○の解説【医師向け】", "△△まとめ（医療従事者向け）", "□□入門【研修医向け】"]:
        assert bp.is_general_reader({"title": t, "categories": ["一般向け"]}) is False
    # マーカー無しは従来どおりタグで判定
    assert bp.is_general_reader({"title": "サプリの話", "categories": ["一般向け"]}) is True


def test_is_general_reader_only_when_general_tag():
    assert bp.is_general_reader({"categories": ["一般向け", "頭痛"]}) is True
    assert bp.is_general_reader({"categories": ["医師向け"]}) is False
    assert bp.is_general_reader({"categories": []}) is False  # 無タグは医療従事者側
    assert bp.is_general_reader({}) is False


def test_split_by_audience_partitions_and_preserves_order():
    arts = [
        {"title": "P1", "categories": ["医師向け"]},
        {"title": "G1", "categories": ["一般向け"]},
        {"title": "P2", "categories": []},          # 無タグ → 医療従事者
        {"title": "G2", "categories": ["頭痛", "一般向け"]},
    ]
    pro, gen = bp.split_by_audience(arts)
    assert [a["title"] for a in pro] == ["P1", "P2"]
    assert [a["title"] for a in gen] == ["G1", "G2"]


def test_build_latest_html_renders_two_labeled_groups():
    arts = [
        {"url": "u1", "title": "医療記事", "categories": ["医師向け"]},
        {"url": "u2", "title": "一般記事", "categories": ["一般向け"]},
    ]
    html = bp.build_latest_html(arts)
    assert "医療従事者向け" in html and "latest-tag-pro" in html
    assert "一般の方向け" in html and "latest-tag-gen" in html
    # 医療記事は pro グループ、一般記事は gen グループに入る（pro が先）
    assert html.index("医療記事") < html.index("一般記事")


def test_build_latest_html_caps_each_group(per=2):
    arts = [{"url": f"u{i}", "title": f"P{i}", "categories": ["医師向け"]} for i in range(5)]
    html = bp.build_latest_html(arts, per_group=2)
    assert html.count('class="latest-item"') == 2


def test_build_latest_html_omits_empty_group():
    arts = [{"url": "u1", "title": "医療のみ", "categories": ["医師向け"]}]
    html = bp.build_latest_html(arts)
    assert "医療従事者向け" in html
    assert "一般の方向け" not in html  # 該当記事ゼロのグループは描画しない


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


# ---- 公開マニフェスト駆動の新着 ----

def test_load_manifest_entries_reads_and_filters(tmp_path):
    import json
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps({"decks": [
        {"slug": "a", "title": "A"}, {"title": "slugなし"}, {"slug": "b"}]}),
        encoding="utf-8")
    entries = bp.load_manifest_entries(mf, "decks")
    assert [e["slug"] for e in entries] == ["a", "b"]


def test_load_manifest_entries_missing_or_broken_returns_empty(tmp_path):
    assert bp.load_manifest_entries(tmp_path / "none.json", "items") == []
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert bp.load_manifest_entries(bad, "items") == []


def test_manifest_slugs_sorts_by_date_desc_when_present():
    entries = [{"slug": "old", "date": "2026-01-01"},
               {"slug": "new", "date": "2026-07-07"},
               {"slug": "nodate"}]
    assert bp.manifest_slugs(entries) == ["new", "old", "nodate"]


def test_manifest_slugs_keeps_order_without_dates():
    entries = [{"slug": "first"}, {"slug": "second"}]
    assert bp.manifest_slugs(entries) == ["first", "second"]


def test_short_label_cuts_pipe_and_boilerplate():
    assert bp.short_label("高血圧の生活指導｜減塩・家庭血圧を1枚に（インフォグラフィック）") == "高血圧の生活指導"
    assert bp.short_label("立ちくらみ対策 | スライド資料") == "立ちくらみ対策"
    assert bp.short_label("") is None


def test_manifest_labels_maps_slug_to_short_title():
    entries = [{"slug": "htn", "title": "高血圧の生活指導｜減塩を1枚に"}, {"slug": "x"}]
    assert bp.manifest_labels(entries) == {"htn": "高血圧の生活指導"}


def test_build_visual_html_has_runtime_hook_ids():
    html = bp.build_visual_html(["ig1"], {}, ["sl1"], {}, 106, "https://t")
    assert 'id="ig-chips"' in html
    assert 'id="slide-list"' in html
    assert 'id="slide-all"' in html


def test_render_page_embeds_manifest_fetch_js():
    html = bp.render_page({"tools_url": "https://t"})
    assert "/infographics/manifest.json" in html
    assert "/slides/manifest.json" in html
    assert "isProTitle" in html  # RSS分類のタイトルマーカー判定
    # 件数プレースホルダが既定値で埋まる
    assert "{{ig_recent_n}}" not in html and "{{slide_recent_n}}" not in html


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


# ---- 統計の自動集計（fetch_stats） ----

def test_fetch_stats_count_entry_urls_unique():
    import fetch_stats as fs
    xml1 = "<urlset><url><loc>https://b/entry/2026/07/08/1</loc></url><url><loc>https://b/about</loc></url></urlset>"
    xml2 = "<urlset><url><loc>https://b/entry/2026/07/08/1</loc></url><url><loc>https://b/entry/2</loc></url></urlset>"
    assert fs.count_entry_urls([xml1, xml2]) == 2  # 重複除外・/entry/のみ


def test_fetch_stats_count_tool_cards():
    import fetch_stats as fs
    html = '<a class="tool-card" href="a.html"></a><a class="tool-card" href="b.html"></a>'
    assert fs.count_tool_cards(html) == 2


def test_fetch_stats_merge_keeps_previous_on_failure():
    import fetch_stats as fs
    prev = {"articles": 1100, "tools": 45, "updated": "2026-07-01"}
    merged = fs.merge_stats({"updated": "2026-07-08", "tools": 46}, prev)
    assert merged["articles"] == 1100  # 取得失敗(キー無し)→既存値保持
    assert merged["tools"] == 46
    assert merged["updated"] == "2026-07-08"


def test_render_page_embeds_stats_json_fetch():
    html = bp.render_page({"tools_url": "https://t"})
    assert "fetch('stats.json')" in html
