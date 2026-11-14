"""公開するファイルだけを配置する。制作記録やテストは配信しない。"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = ['article-updates.html', 'article-updates.css', 'article-updates-widget.js', 'index.html', 'styles.css', 'app.js', 'comment.html', 'guide.html', 'search-index.json', 'catalog-meta.json', 'stats.json', 'CNAME',
         # 検索エンジン向けの案内と、SVGアイコンを読めないブラウザ用のアイコン。
         'robots.txt', 'sitemap.xml', 'favicon.ico']

def main():
    subprocess.run([sys.executable, str(ROOT / 'build_portal.py')], check=True)
    out = ROOT / '_site'
    out.mkdir(exist_ok=True)
    for name in FILES:
        shutil.copyfile(ROOT / name, out / name)
    shutil.copytree(ROOT / 'assets', out / 'assets', dirs_exist_ok=True)
    # カード用の軽量サムネイル。元画像の照合記録（sources.json）は配信しない。
    shutil.copytree(ROOT / 'thumbs', out / 'thumbs', dirs_exist_ok=True, ignore=shutil.ignore_patterns('*.json'))
    # ブログトップの記事カード用。カタログから毎回作るので、リポジトリには置かない。
    sys.path.insert(0, str(ROOT / 'scripts'))
    import blog_thumbs
    try:
        print('blog-thumbs.json:', blog_thumbs.write(out / 'blog-thumbs.json'), 'entries')
    except Exception as exc:  # 対応表が作れなくてもポータルの公開は止めない（ブログは、はてなの画像で表示する）
        print('WARNING: blog-thumbs.json was not built:', exc)
    (out / '.nojekyll').touch()
    print('Staged public site in', out)

if __name__ == '__main__':
    main()
