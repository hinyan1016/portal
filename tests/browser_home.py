import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE = os.environ.get("PORTAL_BASE_URL", "http://127.0.0.1:4180/")
SHOT_DIR = Path(os.environ.get(
    "PORTAL_SCREENSHOT_DIR", Path(__file__).parent / "browser-artifacts"))
SHOT_DIR.mkdir(exist_ok=True)


def verify_layout(page, name, width, height):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.set_viewport_size({"width": width, "height": height})
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(1000)

    assert page.title() == "医知創造ラボ｜医療と健康の知のハブ"
    assert "トップページ試作" not in page.locator("body").inner_text()
    assert page.locator("h1").inner_text() == "医療の知識を、\n日々の安心と診療の力に。"
    assert page.locator("#audience .audience-door").count() == 2
    assert page.locator("#visual-preview img").count() == 3
    assert page.locator("a[href]").count() >= 30
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")

    visuals = page.locator("#visual-preview img").evaluate_all(
        "els => els.map(e => ({complete:e.complete,width:e.naturalWidth,src:e.src}))"
    )
    assert all(item["complete"] and item["width"] > 0 for item in visuals), visuals

    search = page.locator("#site-search")
    search.focus()
    search.fill("頭痛")
    page.wait_for_timeout(1300)
    assert page.locator("#search-results").is_visible()
    assert page.locator("#search-results a").count() >= 1
    search.press("Escape")
    assert not page.locator("#search-results").is_visible()

    page.locator("body").press("Tab")
    assert page.evaluate("document.activeElement && document.activeElement.tagName") in ("A", "BUTTON", "INPUT")

    if width <= 680:
        menu = page.locator(".menu-button")
        assert menu.is_visible()
        menu.click()
        assert menu.get_attribute("aria-expanded") == "true"
        assert page.locator("#global-nav").is_visible()
        menu.click()
        assert menu.get_attribute("aria-expanded") == "false"

    page.screenshot(path=str(SHOT_DIR / f"{name}.png"), full_page=True)
    assert not [error for error in console_errors if "favicon" not in error.lower()], console_errors


def verify_untrusted_feeds(page):
    rss = """<?xml version="1.0" encoding="UTF-8"?><rss><channel>
      <item><title>一般テスト記事</title><link>https://blog.ichisouzo-lab.com/entry/general</link><pubDate>Sun, 06 Sep 2026 10:00:00 +0900</pubDate><category>一般向け</category></item>
      <item><title>医療者テスト記事</title><link>https://blog.ichisouzo-lab.com/entry/pro</link><pubDate>Sun, 06 Sep 2026 09:00:00 +0900</pubDate><category>医師向け</category></item>
      <item><title>読者未分類の記事</title><link>https://blog.ichisouzo-lab.com/entry/other</link><pubDate>Sun, 06 Sep 2026 08:00:00 +0900</pubDate><category>AI</category></item>
    </channel></rss>"""
    page.route(
        "https://blog.ichisouzo-lab.com/rss",
        lambda route: route.fulfill(status=200, body=rss, headers={"content-type": "application/xml", "access-control-allow-origin": "*"}),
    )
    page.route(
        "https://ichisouzo-lab.com/search-index.json",
        lambda route: route.fulfill(status=200, json=[
            {"t": "攻撃テスト", "u": "javascript:alert(1)", "k": "記事"},
            {"t": "安全テスト", "u": "https://blog.ichisouzo-lab.com/entry/safe", "k": "記事"},
        ], headers={"access-control-allow-origin": "*"}),
    )
    page.goto(BASE, wait_until="networkidle")
    page.locator("#site-search").fill("テスト")
    page.wait_for_timeout(300)
    hrefs = page.locator("#search-results a").evaluate_all("els => els.map(e => e.href)")
    assert not any(href.startswith("javascript:") for href in hrefs)
    assert page.get_by_text("安全テスト", exact=True).count() == 1
    assert page.get_by_text("攻撃テスト", exact=True).count() == 0
    assert page.locator('[data-audience="professional"] .article-card').count() == 1
    assert page.get_by_text("読者未分類の記事", exact=True).count() == 0


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    verify_layout(browser.new_page(), "desktop-1440", 1440, 1000)
    verify_layout(browser.new_page(), "mobile-390", 390, 844)
    verify_untrusted_feeds(browser.new_page())
    browser.close()

print("PASS production-candidate desktop-1440 mobile-390 untrusted-feeds")
