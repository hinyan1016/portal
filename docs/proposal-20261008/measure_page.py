"""トップページの重さ・描画時間・文字のコントラストを実測する（読み取りのみ）。

使い方: python measure_page.py <URL またはローカルのフォルダ> <出力フォルダ>
例: python measure_page.py https://ichisouzo-lab.com/ out-live ／ python measure_page.py _site out-proposal

- 初回表示の転送量（種類別・ホスト別）
- 低速回線＋CPU 4倍遅延でのFCP/LCP（Lighthouseのモバイル条件に近い自作計測・参考値）
- 全ページのスクリーンショット（PC/スマホ/ダーク）
- 小さい文字のコントラスト比
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

TARGET = sys.argv[1] if len(sys.argv) > 1 else "https://ichisouzo-lab.com/"
if TARGET.startswith("http"):
    URL = TARGET
else:  # ローカルのフォルダを一時サーバーで配信する（圧縮しないので転送量は本番より大きく出る）
    import functools, http.server, threading

    class _Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    _server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=TARGET))
    threading.Thread(target=_server.serve_forever, daemon=True).start()
    URL = f"http://127.0.0.1:{_server.server_port}/"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
OUT.mkdir(parents=True, exist_ok=True)

LCP_INIT = """
window.__lcp = []; window.__cls = 0;
new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lcp.push({t: e.startTime, size: e.size, tag: e.element ? e.element.tagName : null, cls: e.element ? (e.element.className || '').toString().slice(0,60) : null, url: e.url || ''}); }).observe({type: 'largest-contentful-paint', buffered: true});
new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({type: 'layout-shift', buffered: true});
"""

CONTRAST_JS = """
() => {
  function parse(c){const m=c.match(/rgba?\\(([^)]+)\\)/); if(!m) return null; const p=m[1].split(',').map(s=>parseFloat(s)); return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1};}
  function lum(c){const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b);}
  function bg(el){while(el){const c=parse(getComputedStyle(el).backgroundColor); if(c&&c.a>0.5) return c; el=el.parentElement;} return {r:255,g:255,b:255,a:1};}
  function blend(fg,b){return {r:fg.r*fg.a+b.r*(1-fg.a),g:fg.g*fg.a+b.g*(1-fg.a),b:fg.b*fg.a+b.b*(1-fg.a),a:1};}
  const sels=['.eyebrow','.hero-lead','.format-line span','.format-caption','.brand small','.feature-top span','.feature-foot span','.feature-copy p','.section-aside','.library-note','.filter-label','.result-meta p','.card-category span','.record-note','.card-footer time','.kind-label','.small-note','.tool-path small','.series-index','.series-card .label','.about-details p','.notice p','.footer-bottom span','.footer-bottom a','.global-nav a','.media-art .art-title'];
  const out=[];
  for(const s of sels){const el=document.querySelector(s); if(!el) {out.push({sel:s,missing:true}); continue;} const cs=getComputedStyle(el); const fg=parse(cs.color); const b=bg(el); const f=blend(fg,b); const L1=lum(f),L2=lum(b); const ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05); out.push({sel:s,size:cs.fontSize,weight:cs.fontWeight,color:cs.color,bg:`rgb(${b.r},${b.g},${b.b})`,ratio:Math.round(ratio*100)/100,text:(el.textContent||'').trim().slice(0,24)});}
  return out;
}
"""


def collect_bytes(page, cdp):
    sizes = {}
    meta = {}

    def on_response(params):
        r = params["response"]
        meta[params["requestId"]] = (r["url"], r.get("mimeType", ""), params.get("type", ""))

    def on_finished(params):
        sizes[params["requestId"]] = params.get("encodedDataLength", 0)

    cdp.on("Network.responseReceived", on_response)
    cdp.on("Network.loadingFinished", on_finished)
    return sizes, meta


def summarize(sizes, meta):
    by_type = defaultdict(int)
    by_host = defaultdict(int)
    big = []
    for rid, n in sizes.items():
        url, mime, rtype = meta.get(rid, ("?", "?", "?"))
        by_type[rtype] += n
        by_host[urlparse(url).hostname or "?"] += n
        big.append((n, url))
    big.sort(reverse=True)
    return {
        "requests": len(sizes),
        "total_kb": round(sum(sizes.values()) / 1024),
        "by_type_kb": {k: round(v / 1024) for k, v in sorted(by_type.items(), key=lambda x: -x[1])},
        "by_host_kb": {k: round(v / 1024) for k, v in sorted(by_host.items(), key=lambda x: -x[1])},
        "largest": [(round(n / 1024), u) for n, u in big[:12]],
    }


def run_profile(p, name, viewport, dpr, mobile, throttle, screenshots, dark=False):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport=viewport, device_scale_factor=dpr, is_mobile=mobile, has_touch=mobile,
                              locale="ja-JP", color_scheme="dark" if dark else "light", reduced_motion="reduce")
    if dark:
        ctx.add_init_script("try{localStorage.setItem('ichisouzo-theme','dark')}catch(e){}")
    ctx.add_init_script(LCP_INIT)
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    if throttle:
        cdp.send("Network.emulateNetworkConditions", {
            "offline": False, "latency": 150,
            "downloadThroughput": 1.6 * 1024 * 1024 / 8 * 0.9,
            "uploadThroughput": 750 * 1024 / 8 * 0.9,
        })
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    sizes, meta = collect_bytes(page, cdp)
    t0 = time.time()
    page.goto(URL, wait_until="load", timeout=180000)
    load_s = time.time() - t0
    try:
        page.wait_for_load_state("networkidle", timeout=60000)
    except Exception:
        pass
    page.wait_for_timeout(3000)
    paint = page.evaluate("() => performance.getEntriesByType('paint').map(p => [p.name, Math.round(p.startTime)])")
    lcp = page.evaluate("() => window.__lcp")
    cls = page.evaluate("() => window.__cls")
    initial = summarize(dict(sizes), dict(meta))
    result = {"profile": name, "viewport": viewport, "throttled": throttle, "load_s": round(load_s, 2),
              "paint": paint, "lcp_final": lcp[-1] if lcp else None, "cls": round(cls, 4), "initial": initial}
    if screenshots:
        # 遅延読み込み画像を出すため、ゆっくり最下部までスクロールしてから全体を撮る
        h = page.evaluate("document.body.scrollHeight")
        y = 0
        while y < h:
            y += viewport["height"] // 2
            page.evaluate(f"window.scrollTo(0,{y})")
            page.wait_for_timeout(250)
            h = page.evaluate("document.body.scrollHeight")
        page.wait_for_timeout(2500)
        result["after_scroll"] = summarize(dict(sizes), dict(meta))
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / f"{name}-full.png"), full_page=True)
        page.screenshot(path=str(OUT / f"{name}-first.png"), full_page=False)
        result["contrast"] = page.evaluate(CONTRAST_JS)
        result["page_height"] = page.evaluate("document.body.scrollHeight")
        result["h_overflow"] = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    browser.close()
    return result


with sync_playwright() as p:
    results = []
    results.append(run_profile(p, "desktop", {"width": 1440, "height": 900}, 1, False, False, True))
    results.append(run_profile(p, "mobile", {"width": 390, "height": 844}, 2, True, False, True))
    results.append(run_profile(p, "mobile-dark", {"width": 390, "height": 844}, 2, True, False, True, dark=True))
    results.append(run_profile(p, "mobile-throttled", {"width": 390, "height": 844}, 2, True, True, False))
    (OUT / "audit.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in results:
        print("==", r["profile"], "load", r["load_s"], "s paint", r["paint"], "LCP", r["lcp_final"], "CLS", r["cls"])
        print("   initial:", r["initial"]["total_kb"], "KB /", r["initial"]["requests"], "req", r["initial"]["by_type_kb"])
        if "after_scroll" in r:
            print("   after scroll:", r["after_scroll"]["total_kb"], "KB /", r["after_scroll"]["requests"], "req")
        print("   largest:", r["initial"]["largest"][:6])
