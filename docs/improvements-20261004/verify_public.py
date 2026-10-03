"""本番配信のテキスト資産を検収済みローカル版と照合する。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = ['index.html', 'app.js', 'styles.css', 'guide.html', 'search-index.json', 'catalog-meta.json', 'comment.html']


def digest(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def main():
    results = []
    for name in FILES:
        url = 'https://ichisouzo-lab.com/' + ('' if name == 'index.html' else name)
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Ichisouzo-Portal-QA/1.0'}), timeout=30) as response:
            body = response.read()
            result = {'file': name, 'url': url, 'status': response.status,
                      'expected_sha256': digest((ROOT / name).read_bytes()), 'actual_sha256': digest(body)}
            result['matches'] = result['expected_sha256'] == result['actual_sha256']
            results.append(result)
    report = {'checked': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS' if all(r['status'] == 200 and r['matches'] for r in results) else 'FAIL',
              'checks': results}
    (HERE / 'public-qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
