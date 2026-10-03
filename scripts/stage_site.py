"""公開するファイルだけを配置する。制作記録やテストは配信しない。"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = ['index.html', 'styles.css', 'app.js', 'comment.html', 'guide.html', 'search-index.json', 'catalog-meta.json', 'stats.json', 'CNAME']

def main():
    subprocess.run([sys.executable, str(ROOT / 'build_portal.py')], check=True)
    out = ROOT / '_site'
    out.mkdir(exist_ok=True)
    for name in FILES:
        shutil.copyfile(ROOT / name, out / name)
    shutil.copytree(ROOT / 'assets', out / 'assets', dirs_exist_ok=True)
    (out / '.nojekyll').touch()
    print('Staged public site in', out)

if __name__ == '__main__':
    main()
