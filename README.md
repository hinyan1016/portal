# 統合ポータル（医知創造ラボ）

apex `ichisouzo-lab.com` 用のポータル `index.html` を生成する。

## 構成

- `src/index.html`: トップページHTMLの正本
- `styles.css`: トップページのスタイル
- `app.js`: RSS・図解マニフェスト・検索の実行時更新
- `build_portal.py`: 正本から `index.html` を生成し、横断検索用 `search-index.json` を更新

## 再生成

```bash
/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe build_portal.py
```

- データ源: `../medical-content/blog/seo-improvement/corpus_cache.json`
- ツール走査: `../medical-ddx-tools/`
- 手動調整: `featured.json`（注目記事・代表ツール）、`config.json`（カテゴリ選定・各URL）

単独クローンでは `index.html` の再生成だけを行い、同梱済みの `search-index.json` を保持する。
上記2つの隣接データがある制作ワークスペースでは、検索インデックスも同時更新する。

新着記事はブログRSS、図解は公開マニフェストからブラウザー上で更新する。
取得に失敗した場合は `src/index.html` 内の確認済み内容を表示する。

診断支援ツール件数は表示しない。`stats.json`、トップ内リンク、ツール一覧カードで
定義が一致していないため、件数の定義が統一されるまでは数値を置かない。

## テスト

```bash
/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q
```

ブラウザー統合テストは、ローカルサーバーをポート4180で起動してから実行する。

```bash
/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe tests/browser_home.py
```

## デプロイ（最終工程・要承認）

現在は `CNAME = ichisouzo-lab.com` と GitHub Pages が設定済み。`main` へのpushで
`.github/workflows/pages.yml` が自動公開するため、pushは最終承認後に行う。

戻す場合は、公開に使用したコミットを指定して `git revert <公開コミット>` を実行し、
revertコミットを `main` へpushする。Pagesの再デプロイ完了後、公開トップを確認する。
