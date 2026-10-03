"""公開前にガイドの全リンクを実際のHTTP接続で確認する。"""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, quote
import json
import subprocess
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
soup = BeautifulSoup((HERE / 'guide-revised.html').read_text(encoding='utf-8'), 'html.parser')
destinations = {}
for tag in soup.find_all(['a', 'img']):
    attr = 'href' if tag.name == 'a' else 'src'
    value = tag.get(attr, '')
    parts = urlsplit(value)
    if parts.scheme != 'https':
        continue
    # クエリで絞り込む入口はブラウザー検査でも確認する。
    key = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
    item = destinations.setdefault(key, {'url': key, 'attributes': [], 'variants': []})
    if attr not in item['attributes']:
        item['attributes'].append(attr)
    if value not in item['variants']:
        item['variants'].append(value)

results = []
for item in destinations.values():
    parts = urlsplit(item['url'])
    url = urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe='/%:@'), '', ''))
    method = 'HEAD' if item['attributes'] == ['src'] else 'GET'
    command = ['curl.exe', '--location', '--max-redirs', '5', '--proto', '=https',
               '--proto-redir', '=https', '--max-time', '30', '--silent', '--show-error',
               '--output', 'NUL', '--write-out', '%{http_code}\n%{url_effective}', url]
    if method == 'HEAD':
        command.insert(1, '--head')
    response = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    lines = response.stdout.splitlines()
    status = int(lines[0]) if lines and lines[0].isdigit() else 0
    final_url = lines[1] if len(lines) > 1 else None
    passed = response.returncode == 0 and status == 200
    item.update(method=method, status=status, final_url=final_url, result='pass' if passed else 'fail')
    if response.returncode:
        item['error'] = response.stderr.strip()
    results.append(item)
    print(f'[{"OK" if passed else "NG"}] {status} {item["url"]}', flush=True)

report = {'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
          'source': 'guide-revised.html',
          'request_policy': {'transport': 'curl.exe', 'method': 'GET (image HEAD)',
                             'concurrency': 1, 'attempts': 1, 'timeout_seconds': 30,
                             'response_bodies_saved': False},
          'unique_https_destinations': len(results),
          'pass': sum(item['result'] == 'pass' for item in results),
          'fail': sum(item['result'] == 'fail' for item in results),
          'blocked': 0, 'results': results}
(HERE / 'guide-link-qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
raise SystemExit(0 if report['fail'] == 0 else 1)
