# 医知創造ラボ ポータル

公開サイト: https://ichisouzo-lab.com/ （GitHub Pages）

## 構成

- `src/index.html`：トップページの正本。`build_portal.py` で `index.html` に反映。
- `styles.css`：レスポンシブ表示・ダークモード。
- `guide.html`：目的別の使い方と保存機能の案内。
- `app.js`：横断検索、読者・形式・テーマ絞り込み、並べ替え、保存、閲覧履歴、検索条件共有。
- `search-index.json`：公開コンテンツのカタログ。記事・図解・動画・スライド・ツール。
- `scripts/refresh_catalog.py`：公開RSS・サイトマップ・図解/スライドマニフェスト・公開ツール一覧から更新。
- `scripts/series_metadata.json`：公開本文などで確認したシリーズの回番号。日次更新でも保持する。
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

- 対象読者は公開記事のカテゴリー・明示的な対象者表記、資料の対象者・タグで判定。資料に表示がない場合は、同じ公開記事の読者区分を継承する。未分類は「読者区分なし」とし、一般向け/医療従事者向けの絞り込みに混ぜない。
- `refresh_catalog.py --complete-audience` は未分類記事の公開ヘッダーを追加確認する任意の補完処理。通常の日次更新は補完済みの区分と根拠を保持する。明示されていない読者区分を推測しない。
- 検索はタイトル・タグのAND検索。全角/半角・英字大小文字に加え、「もの忘れ／物忘れ」などの表記ゆれと一部の薬剤略語を対応させる。本文全文はブログ側の検索へ案内。
- 「すべて」では同じ公開記事に紐づく記事・動画・図解・スライドを1テーマにまとめる。各形式のリンクと保存先は元のURLを維持し、形式を絞ると個別表示する。タイトルが似ているだけのコンテンツは結合しない。
- 「おすすめ順」は媒体と読者を組み合わせた並び。個人情報による推薦ではない。番号を確認できたシリーズは第1回からの順で表示し、次の連続する回へのリンクを設ける。
- しおりは最大200件、閲覧履歴は最大30件。localStorageのみで、このブラウザーに保存。サーバー送信・アカウント・端末間同期はない。保存不可の場合は画面に表示。
- 検索条件はURLに保存できる。ブラウザーの戻る/進む、検索リンクの共有に対応。
- 公開フィード取得に失敗しても同梱カタログで検索できる。画像はthumb→実図解→形式の図柄の順で代替。
- 表示される日付は記事/資料の公開日。日付不明のものに推測の日付を付けない。
- トップのPICK UPは編集枠。公開カタログの更新とは別に `src/index.html` で選定する。

## テスト

```powershell
python -m pytest tests -q -p no:cacheprovider --basetemp ./test-tmp
python tests/browser_redesign.py
python tests/browser_runtime.py
node --check app.js
python scripts/stage_site.py
```

`browser_redesign.py` は自前の一時HTTPサーバーを使う。5画面幅、検索・絞り込み、URL復元、保存・履歴・テーマの永続化、キーボード、壊れたデータ・画像・通信失敗を検証。
新ガイドの各画面幅・テーマ切替、実カタログの検索とシリーズ順も検証する。`browser_runtime.py` は制御したカタログとRSSで、検索別名・テーマの結合境界・形式ごとの保存・シリーズ・更新時のメタデータ保持を検証する。
`browser_home.py` と `browser_image_fallback.py` は旧トップのテスト（履歴用）。新版の検収には使わない。

## 公開（最終工程・要承認）

`main` へのpushで `.github/workflows/pages.yml` が公開するため、完成版の確認と先生の最終承認後に行う。
公開対象は `_site/` のみ。制作記録・テスト・ローカルメタデータは配信しない。

既存の日次更新に公開カタログ更新を追加。`Update portal stats` 完了後に `workflow_run` でPagesを再配信する。
GITHUB_TOKENによる自動コミットのpushだけに再配信を依存させない。新ワークフローの実運用確認は公開後に行う。

承認後はremoteの最新状態を確認し、変更分だけを統合。公開完了後に本番URLで検索・しおり・モバイル表示を再確認する。
戻す場合は公開コミットを `git revert` し、mainへpushして再配信を確認する。
