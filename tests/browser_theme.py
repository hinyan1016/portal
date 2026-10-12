"""初期描画・保存済み選択・OS配色・リロード・ガイド間の配色を実Chromiumで検証。"""
import argparse,functools,http.server,json,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url');ap.add_argument('--shots',required=True);a=ap.parse_args()
    shots=Path(a.shots);shots.mkdir(parents=True,exist_ok=True);server=None
    if a.url:base=a.url.rstrip('/')+'/'
    else:
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT)))
        threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)+'/'
    report={'url':base,'cases':[]}
    cases=[('first-os-light',None,'light','dark'),('first-os-dark',None,'dark','dark'),('saved-light-os-dark','light','dark','light'),('saved-dark-os-light','dark','light','dark'),('invalid','invalid','light','dark'),('storage-unavailable',None,'light','dark')]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();report['browser']=browser.version
            for name,saved,os_color,expected in cases:
                ctx=browser.new_context(viewport={'width':1280,'height':900},color_scheme=os_color)
                if saved:
                    ctx.add_init_script("if(!sessionStorage.getItem('theme-test-seeded')){localStorage.setItem('ichisouzo-theme',"+json.dumps(saved)+");sessionStorage.setItem('theme-test-seeded','1');}")
                if name=='storage-unavailable':
                    ctx.add_init_script("Storage.prototype.getItem=function(){throw new Error('test storage unavailable')};Storage.prototype.setItem=function(){throw new Error('test storage unavailable')};")
                pg=ctx.new_page();errors=[];pg.on('pageerror',lambda e:errors.append(str(e)))
                response=pg.goto(base,wait_until='domcontentloaded');assert response.status==200
                source=response.text();assert '<html lang="ja" data-theme="dark">' in source
                assert source.index('localStorage.getItem(\'ichisouzo-theme\')')<source.index('href="styles.css"')
                pg.wait_for_selector('.content-card')
                assert pg.evaluate('document.documentElement.dataset.theme')==expected,(name,expected)
                assert pg.locator('#theme-toggle').get_attribute('aria-pressed')==str(expected=='dark').lower()
                initial_bg=pg.evaluate('getComputedStyle(document.body).backgroundColor')
                pg.screenshot(path=str(shots/(name+'.png')))
                if name!='storage-unavailable':
                    switched='light' if expected=='dark' else 'dark'
                    pg.click('#theme-toggle');assert pg.evaluate('document.documentElement.dataset.theme')==switched
                    assert pg.evaluate("localStorage.getItem('ichisouzo-theme')")==switched
                    pg.reload(wait_until='domcontentloaded');pg.wait_for_selector('.content-card')
                    assert pg.evaluate('document.documentElement.dataset.theme')==switched
                    pg.goto(base+'guide.html',wait_until='domcontentloaded')
                    assert pg.evaluate('document.documentElement.dataset.theme')==switched
                    pg.click('#guide-theme-toggle');assert pg.evaluate('document.documentElement.dataset.theme')==expected
                    pg.goto(base,wait_until='domcontentloaded');pg.wait_for_selector('.content-card')
                    assert pg.evaluate('document.documentElement.dataset.theme')==expected
                else:
                    pg.reload(wait_until='domcontentloaded');pg.wait_for_selector('.content-card');assert pg.evaluate('document.documentElement.dataset.theme')=='dark'
                assert not errors,errors
                report['cases'].append({'name':name,'os':os_color,'saved':saved,'initial':expected,'initialBackground':initial_bg,'reload':True,'errors':errors})
                print('PASS '+name,flush=True);ctx.close()
            # アプリJSが動く前のHTML/CSSだけでも、早期復元とデフォルト配色が成立する。
            for saved,expected in [(None,'dark'),('light','light'),('dark','dark')]:
                ctx=browser.new_context(color_scheme='light')
                if saved:ctx.add_init_script("localStorage.setItem('ichisouzo-theme',"+json.dumps(saved)+");")
                ctx.route('**/app.js',lambda route:route.abort())
                pg=ctx.new_page();pg.goto(base,wait_until='domcontentloaded')
                assert pg.evaluate('document.documentElement.dataset.theme')==expected
                assert pg.evaluate('getComputedStyle(document.documentElement).colorScheme')==expected
                ctx.close()
            ctx=browser.new_context(java_script_enabled=False,color_scheme='light');pg=ctx.new_page();pg.goto(base,wait_until='domcontentloaded')
            assert pg.locator('html').get_attribute('data-theme')=='dark';ctx.close()
            report['beforeAppJsVerified']=True;report['jsDisabledDefaultDark']=True
            browser.close()
    finally:
        if server:server.shutdown();server.server_close()
    (shots/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
