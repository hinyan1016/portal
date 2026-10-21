# 医知創造ラボ ポータル

公開サイト: https://ichisouzo-lab.com/ （GitHub Pages）

## 構成

- `src/index.html`：トップページの正本。`build_portal.py` で `index.html` に反映。
- `styles.css`：レスポンシブ表示・ダークモード。
- `guide.html`：目的別の使い方と保存機能の案内。
- `app.js`：横断検索、読者・形式・テーマ絞り込み、並べ替え、保存、閲覧履歴、検索条件共有。
- `search-index.json`：公開コンテンツのカタログ。記事・図解・動画・スライド・ツール。
- `scripts/refresh_catalog.py`：公開RSS・サイトマップ・図解/スライドマニフェスト・公開ツール一覧から更新。
- `scripts/build_thumbs.py`：図解カード用の軽量サムネイル `thumbs/<slug>.webp`（16:9・幅800px以下）を作る。元画像の大きさを `thumbs/sources.json` に記録し、変わった図解だけ作り直す。
- `scripts/build_brand_images.py`：SNS共有画像 `assets/og-image.png` とアイコンを書き出す。デザインを変えたときだけ手元で実行。
- `scripts/series_metadata.json`：公開本文などで確認したシリーズの回番号。日次更新でも保持する。
- `scripts/stage_site.py`：公開用ファイルだけを `_site/` に配置。

## 制作・確認

PowerShellでは最初に `$env:PYTHONIOENCODING='utf-8'` を設定。

```powershell
python scripts/build_thumbs.py --tools-dir ../medical-ddx-tools
python scripts/refresh_catalog.py
python build_portal.py
python -m http.server 4189 --bind 127.0.0.1
```

`--tools-dir` は省略可。公開版と同じ大きさのローカル画像だけを流用し、ほかは公開URLから取得する。
`build_portal.py` は明朝見出しに使う文字を `src/index.html` と `guide.html` から集め、Webフォントの読み込みURL（`text=`）を書き換える。

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
- カタログは6時間ごとに更新する（`Update portal stats`）。`catalog-meta.json` の更新時刻が12時間以内なら、表示時に公開RSS（約1.6MB）・資料一覧を取得しない。GitHubの定期実行は数時間遅れることがあるため、更新2回分の余裕を取る。古いときだけ、表示後の空き時間に取得して反映する。
- 公開フィード取得に失敗しても同梱カタログで検索できる。図解の画像は `thumbs/` の軽量版だけを使い、原寸PNG（1枚約2MB）は読まない。軽量版が無いものは形式の図柄で代替。
- 文字はOS標準の日本語フォント（Mac/iPhoneはヒラギノ、WindowsはBIZ UDPゴシック）。明朝の見出しだけ Noto Serif JP を使う文字に絞って読む。文字サイズは rem 指定で、ブラウザーの文字サイズ設定を反映する。
- スマホ（幅680px以下）は一覧の初期表示と「もっと見る」を6件ずつ、PCは9件ずつ。
- 表示される日付は記事/資料の公開日。日付不明のものに推測の日付を付けない。
- トップのPICK UPは編集枠。公開カタログの更新とは別に `src/index.html` で選定する。
- トップの枠のうち、**手で選ぶのは PICK UP と制作こぼれ話だけ**。ほかの枠は下の「トップの自動更新枠」で6時間ごとに更新する。

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

定期更新（6時間ごと）でサムネイル生成と公開カタログ更新を行う。`Update portal stats` 完了後に `workflow_run` でPagesを再配信する。
GITHUB_TOKENによる自動コミットのpushだけに再配信を依存させない。新ワークフローの実運用確認は公開後に行う。

承認後はremoteの最新状態を確認し、変更分だけを統合。公開完了後に本番URLで検索・しおり・モバイル表示を再確認する。
戻す場合は公開コミットを `git revert` し、mainへpushして再配信を確認する。

## トップの自動更新枠（2026-10-21）

`scripts/refresh_home.py` が公開情報だけから `home-feed.json` を作り、`build_portal.py` が `src/index.html` の
目印（`<!-- MEDICAL_NEWS -->` など6つ）へ埋め込む。定期実行 `Update portal stats` が、カタログの更新に続けて
両方を実行し、変わったファイルをコミットする（Pages の再配信は従来どおり）。設定は `home-config.json`。

| 枠 | データの出どころ | 選び方 |
|---|---|---|
| 医学の新着記事と解説動画 | ブログRSS | `medical_categories` のどれかが付いた最新3件。説明はリード文の「この記事では〜」の文（無ければ最初の文）。末尾の【医師向け】などは読者表示に回す |
| 解説動画のリンク | 記事に埋め込んだYouTube ＋ チャンネルの公開フィード | 公開フィードで見えた動画だけリンクする。限定公開や公開前の動画はリンクしない（見えた動画IDは `scripts/home_state.json` に保持） |
| 最近更新した記事 | サイトマップの lastmod ＋ 公開本文 | 下の「最近更新した記事」の自動登録を参照 |
| 実用ツールの近道（医療従事者向け） | ツール一覧（tools のトップ） | 初めて見た日が新しいツール2件 ＋ 定番3件（`pro_tool_staples`） |
| 実用ツールの近道（一般向け） | 配布資料マニフェスト | 対象が患者・一般・ご家族の資料で、初めて見た日が新しい2件 |
| オフライン版 | GitHub の最新リリース `offline-v*` | 版・日付（リリース名か本文冒頭の日付）・ZIPの大きさ・収録件数（本文から読む。読めなければ件数なしの文） |

- 枠ごとに取得・検証し、失敗した枠は前回のデータのまま残す。不正な値（想定外のURL・動画ID・日付）は埋め込まずに失敗させる。
- ツールと配布資料の「初めて見た日」は、導入時に tools リポジトリの追加日で埋めた。以後は定期実行で初めて見た日を記録する。
- オフライン版の注意書き（`download-note`）と見出しは `src/index.html` の固定文。版ごとに内容が変わったら手で直す。

```powershell
python scripts/refresh_home.py --dry-run   # 書き込まずに結果を表示
python scripts/refresh_home.py
python build_portal.py
python -m pytest tests/test_home_feed.py -q -p no:cacheprovider
```

## 制作こぼれ話を追加する

`columns.json` に、日付・タイトル・短文・関連リンクを追加する。HTMLの知識や外部サービスの登録は不要。
配列の先頭がトップページの先頭になる。最新3件をカード表示し、4件目以降も「以前の制作こぼれ話を読む」で開ける。
`date` はこのコラムを掲載した日（YYYY-MM-DD）。関連動画や記事の公開日とは区別する。
`body` は普通の文章。空行（JSONでは `\n\n`）で段落を分けられる。HTMLは安全のため文字として表示する。
`id` は重複しない英小文字・数字・ハイフン、`links` は任意でHTTPSのURLを使う。

```json
{
  "id": "new-production-note",
  "date": "2026-10-12",
  "title": "コラムの見出し",
  "body": "ここに短い文章を書く。",
  "links": [{"label": "関連記事を読む", "url": "https://blog.ichisouzo-lab.com/entry/2026/10/08/121828"}]
}
```

```powershell
python -X utf8 build_portal.py
python -m pytest tests/test_columns.py -q -p no:cacheprovider
```

生成した `index.html` とデータ・関連ソースをコミットし、公開承認後に `main` へpushする。
公開後は https://ichisouzo-lab.com/#columns で文章・リンク・スマホ表示を確認する。
制作時の実感として書き、AIの医学的正確性や人間以上の性能を客観的に保証する表現にはしない。
2026-10-12の初期3話は本人の発言に基づく制作メモ。記事や動画の公開日を変更しない。

同日のPICK UPはMNIアトラスの実ツール画面（`assets/mni-atlas-learning-20261012.webp`）と直接リンクを掲載。
正本の編集箇所は `src/index.html` の `.hero-feature`。制作記事へのリンクをフッター側に置いている。

## 初回の配色（2026-10-12）

未選択時はOS設定にかかわらず既存のダークテーマを使う。`src/index.html` と `guide.html` の
`html[data-theme="dark"]` を初期値にし、CSSより前に保存済み `ichisouzo-theme`（light/dark）だけを反映する。
明示的に選んだライト／ダークは従来どおり保存し、リロードやページ移動でも尊重する。
保存値が不正・保存領域にアクセスできない・JavaScriptが無効の場合も、未選択時のダークを維持する。
配色そのものとコンテンツは変更していない。

```powershell
python -X utf8 tests/browser_theme.py --shots <検証画像の保存先>
```

## 最近更新した記事

既存記事の改訂は article-updates.json に載る。2026-10-21 から、本文に日付付きの改訂告知がある改訂は定期実行が自動で登録する（`source: auto`）。告知の無い改訂は従来どおり公開確認後に手で登録する。登録・検証・両トップへの初回設置・差し戻しは [更新登録手順](docs/article-updates-workflow.md) を参照。新着の公開日やRSS順位とは独立している。


### 2026-10-18 トップページの掲載更新
- 初回表示は薄茶色のライトテーマ。保存済みのライト／ダーク選択を優先する（上記10/12時点の初期ダーク設定を変更）。
- （2026-10-21 から自動更新。上の「トップの自動更新枠」を参照）`src/index.html` の `medical-news` に公開確認済みの医学記事・対応YouTubeを掲載。記事の公開日を表示し、動画公開日や既存記事の改訂日として流用しない。
- 掲載を入れ替える際は記事本文・公開日時とYouTube oEmbedのタイトルを確認する。新着記事と `article-updates.json` の改訂履歴を混同しない。
- 実用ツールには日常生活自立度・MNIアトラス・不眠の配布資料を追加。記事本文、共有更新台帳、コラム本文は変更しない。
- `python build_portal.py` 後、`python -m pytest -q` と `python tests/browser_theme.py --shots <出力先>` で検証する。幅320/390/768/1440で新着・ツール・改訂履歴・コラムと検索を確認する。
- 公開確認の根拠: `docs/home-refresh-20261018.md`。
