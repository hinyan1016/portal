import concurrent.futures,json,urllib.request,urllib.error,pathlib
root=pathlib.Path('docs/redesign-20260929')
urls=json.loads((root/'links-to-check.json').read_text(encoding='utf-8'))
def check(url):
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as r:
   return {'url':url,'status':r.status,'final':r.url}
 except Exception as e:return {'url':url,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(check,urls))
(root/'links-qa.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('Checked',len(results),'links; OK:',sum(x.get('status')==200 for x in results))
print(json.dumps([x for x in results if x.get('status')!=200],ensure_ascii=False))
