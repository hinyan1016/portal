# 医知創造ラボ ポータル

公開サイト: https://ichisouzo-lab.com/ （GitHub Pages）

## 構成

- `src/index.html`：トップページの正本。`build_portal.py` で `index.html` に反映。
- `styles.css`：レスポンシブ表示・ダークモード。
- `app.js`：横断検索、読者・形式・テーマ絞り込み、並べ替え、保存、閲覧履歴、検索条件共有。
- `search-index.json`：公開コンテンツのカタログ。記事・図解・動画・スライド・ツール。
- `scripts/refresh_catalog.py`：公開RSS・サイトマップ・図解/スライドマニフェスト・公開ツール一覧から更新。
- `scripts/stage_site.py`：公開用ファイルだけを `_site/` に配置。

## 制作・確認

PowerShellでは最初に `$env:PYTHONIOENCODING='utf-8'` を設定。

```powershell
python scripts/refresh_catalog.py
python build_portal.py
python -m http.server 4189 --bind 127.0.0.1
```

ブラウザーで http://127.0.0.1:4189/ を開く。

ローカルに記事メタデータがある場合は `refresh_catalog.py --corpus <corpus_cache.json>` で補完できる。
**公開サイトマップに含まれ、draftでない記事だけ**を取り込む。本文・編集URL・Entry IDは出力しない。
通常のHTMLビルドは検索カタログを保持する。旧フォルダ走査による形式への書き戻しを行わない。

## 機能・データの扱い

- 対象読者は公開記事のカテゴリー、資料の対象者・タグで判定。未分類は「読者区分なし」とし、一般向け/医療従事者向けの絞り込みに混ぜない。専門家向けタイトルを優先。
- 検索はタイトル・タグのAND検索。全角/半角と英字大小文字を正規化。本文全文はブログ側の検索へ案内。
- 「おすすめ順」は媒体と読者を組み合わせた並び。同じ記事の別媒体は初期表示で重複しにくくする。個人情報による推薦ではない。
- しおりは最大200件、閲覧履歴は最大30件。localStorageのみで、このブラウザーに保存。サーバー送信・アカウント・端末間同期はない。保存不可の場合は画面に表示。
- 検索条件はURLに保存できる。ブラウザーの戻る/進む、検索リンクの共有に対応。
- 公開フィード取得に失敗しても同梱カタログで検索できる。画像はthumb→実図解→形式の図柄の順で代替。
- 表示される日付は記事/資料の公開日。日付不明のものに推測の日付を付けない。
- トップのPICK UPは編集枠。公開カタログの更新とは別に `src/index.html` で選定する。

## テスト

```powershell
python -m pytest tests -q -p no:cacheprovider --basetemp ./test-tmp
python tests/browser_redesign.py
node --check app.js
python scripts/stage_site.py
```

`browser_redesign.py` は自前の一時HTTPサーバーを使う。5画面幅、検索・絞り込み、URL復元、保存・履歴・テーマの永続化、キーボード、壊れたデータ・画像・通信失敗を検証。
`browser_home.py` と `browser_image_fallback.py` は旧トップのテスト（履歴用）。新版の検収には使わない。

## 公開（最終工程・要承認）

`main` へのpushで `.github/workflows/pages.yml` が公開するため、完成版の確認と先生の最終承認後に行う。
公開対象は `_site/` のみ。制作記録・テスト・ローカルメタデータは配信しない。

既存の日次更新に公開カタログ更新を追加。`Update portal stats` 完了後に `workflow_run` でPagesを再配信する。
GITHUB_TOKENによる自動コミットのpushだけに再配信を依存させない。新ワークフローの実運用確認は公開後に行う。

承認後はremoteの最新状態を確認し、変更分だけを統合。公開完了後に本番URLで検索・しおり・モバイル表示を再確認する。
戻す場合は公開コミットを `git revert` し、mainへpushして再配信を確認する。
