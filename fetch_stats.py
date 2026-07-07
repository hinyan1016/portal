"""ヒーロー統計（公開記事数・診断ツール数・スライド数・インフォ数）を集計して stats.json に書く。

データ源（すべて公開データ・認証不要）:
  - 公開記事数: ブログの sitemap.xml（サイトマップインデックス→月別サイトマップの /entry/ URL数）
  - 診断ツール数: tools サイトのトップ index.html の tool-card 数
  - スライド/インフォ数: 各 manifest.json の件数

GitHub Actions の日次cron（.github/workflows/update-stats.yml）から実行され、
変化があれば stats.json がコミット→Pagesデプロイされる。ポータルのJSが実行時に読む。
取得失敗時は既存 stats.json の値を保持する（0で上書きしない）。
"""
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

BLOG_SITEMAP = "https://blog.ichisouzo-lab.com/sitemap.xml"
TOOLS_INDEX = "https://tools.ichisouzo-lab.com/"
SLIDES_MANIFEST = "https://tools.ichisouzo-lab.com/slides/manifest.json"
IG_MANIFEST = "https://tools.ichisouzo-lab.com/infographics/manifest.json"

LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
TOOL_CARD_RE = re.compile(r'class="tool-card"')


def http_get(url, timeout=30):
    """URLをUTF-8テキストで取得する。"""
    req = urllib.request.Request(url, headers={"User-Agent": "ichisouzo-portal-stats/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def sitemap_locs(xml_text):
    """サイトマップXML中の <loc> URL のリストを返す。"""
    return LOC_RE.findall(xml_text)


def count_entry_urls(sitemap_xmls):
    """月別サイトマップ群から公開記事（/entry/ を含むURL）のユニーク数を数える。"""
    urls = set()
    for xml_text in sitemap_xmls:
        for u in sitemap_locs(xml_text):
            if "/entry/" in u:
                urls.add(u)
    return len(urls)


def count_tool_cards(html_text):
    """ツール一覧HTML中の tool-card の数を返す。"""
    return len(TOOL_CARD_RE.findall(html_text))


def fetch_article_count():
    """サイトマップインデックスを辿って公開記事総数を返す。"""
    index_xml = http_get(BLOG_SITEMAP)
    sub_urls = [u for u in sitemap_locs(index_xml) if "sitemap" in u]
    return count_entry_urls(http_get(u) for u in sub_urls)


def merge_stats(new, previous):
    """新集計を既存値とマージする（新値が正の数のときのみ採用）。"""
    out = dict(previous)
    for k, v in new.items():
        if isinstance(v, int) and v > 0:
            out[k] = v
        elif k not in out and not isinstance(v, int):
            out[k] = v
    out["updated"] = new.get("updated") or out.get("updated", "")
    return out


def main():
    here = Path(__file__).resolve().parent
    stats_path = here / "stats.json"
    previous = {}
    if stats_path.is_file():
        try:
            previous = json.loads(stats_path.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}

    new = {"updated": date.today().isoformat()}
    try:
        new["articles"] = fetch_article_count()
    except OSError as e:
        print(f"[warn] articles取得失敗: {e}", file=sys.stderr)
    try:
        new["tools"] = count_tool_cards(http_get(TOOLS_INDEX))
    except OSError as e:
        print(f"[warn] tools取得失敗: {e}", file=sys.stderr)
    try:
        new["slides"] = len(json.loads(http_get(SLIDES_MANIFEST)).get("decks") or [])
    except (OSError, ValueError) as e:
        print(f"[warn] slides取得失敗: {e}", file=sys.stderr)
    try:
        new["infographics"] = len(json.loads(http_get(IG_MANIFEST)).get("items") or [])
    except (OSError, ValueError) as e:
        print(f"[warn] infographics取得失敗: {e}", file=sys.stderr)

    merged = merge_stats(new, previous)
    stats_path.write_text(
        json.dumps(merged, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8", newline="\n")
    print(f"stats.json: {merged}")


if __name__ == "__main__":
    main()
