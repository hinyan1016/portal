# 統合ポータル「医知創造ラボ」HANDOFF（別PC引き継ぎ）

最終更新: 2026-06-15

apex `ichisouzo-lab.com` を玄関にした、ブログ＋ツール＋YouTube＋図解の統合ポータル。
このファイルは**別PCで作業を再開するための引き継ぎ**（`~/.claude` のメモリは別PCに転送されないため、要点をリポに残す）。

## リポジトリ構成（ワークスペース = `Claude_task_new/`・git管理しない。各サブフォルダが独立リポ）

| ローカル | GitHub | ブランチ | 公開先 |
|---|---|---|---|
| `portal/` | hinyan1016/portal | main | **apex `ichisouzo-lab.com`**（Pages=GitHub Actions） |
| `medical-ddx-tools/` | hinyan1016/medical-ddx-tools | master | `tools.ichisouzo-lab.com`（Pages） |
| `symptom-checker/` | hinyan1016/symptom-checker | main | `check.ichisouzo-lab.com` |
| `medical-content/` | hinyan1016/medical-content（private） | main | 非公開（記事・スライド・図解の元データ） |
| （ブログ本体） | はてなブログ | — | `blog.ichisouzo-lab.com` |

**別PCセットアップ**: `Claude_task_new/` を作り、その中に上記4リポを**兄弟フォルダ**として clone。
`build_portal.py` / `build_infographic_gallery.py` は相対パスで兄弟リポ（medical-content・medical-ddx-tools）を参照するため、この配置が必須。

## 環境
- Python: `/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe`（pytest, Pillow 導入済み）
- gh CLI: `export PATH="$PATH:/c/Program Files/GitHub CLI"`
- git（OneDrive対策）: 各リポで `git config windows.appendAtomically false`

## ポータルの作り方・更新
```bash
cd portal
<PY> -m pytest tests -q          # 26件
<PY> build_portal.py             # index.html + search-index.json を生成
git add -A && git commit && git push   # GitHub Actions が自動デプロイ(~40s)
```
- 生成元: `config.json`(ブランド/カテゴリ選定/各URL) + `featured.json` + 兄弟リポ走査。
- **正準データ**: `medical-content/blog/seo-improvement/corpus_cache.json`（list・記事の title/url/categories/draft）。
  ※`inventory_v2.csv` は旧URL欠損で使わない。
- ポータルの主な部品（すべて `build_portal.py` 生成・単一HTML/CSS/JS内包）:
  - ヒーロー: 明朝見出し＋統計＋**検索窓**＋CTA
  - **検索**: `search-index.json`(全コンテンツ横断・初回フォーカスでfetch)＋はてな全文検索リンク
  - **最新の記事**: ブログRSS(`blog.ichisouzo-lab.com/rss`・CORS `*`)を**実行時取得して自動更新**（#latest-wrap・失敗時はビルド時HTMLにフォールバック）
  - カテゴリカード→はてな自動カテゴリページ（中身は自動最新）
  - ツール/図解/スライド（medical-ddx-tools走査）＋**画像版インフォグラフィック集**リンク
  - **監修者コメント**: `comment.html`(noindex)を`<iframe>`埋め込み＝SEO非加算。編集は `comment.html` の `<!--▼▼-->` 内を書き換えてpushで即反映
  - フッター/ABOUT(config.intro)

## 画像版インフォグラフィック・ギャラリー
```bash
<PY> medical-content/build_infographic_gallery.py   # 再実行で最新化
```
- 出力: `medical-ddx-tools/infographics-gallery/`（WebP + index.html + gallery.json）。公開: `tools.ichisouzo-lab.com/infographics-gallery/`（現在51点）。
- ロジック: youtube-slides/*の本番インフォgr1枚選別→**フォルダ内最頻出の記事URL=本来の記事**判定→公開判定(corpus照合＋6月分ライブ<title>)→HTML版がある記事は重複除外→記事URLでdedup→WebP最適化。
- 注意: 全PNGは7,317枚2.6GB（載せ不可）。スライドPNGは対象外（インフォグラフィックのみ）。

## DNS（Cloudflare・zone ichisouzo-lab.com / account 06f2333613e5611cdfbf5d16101df2d9）
- apex `@` CNAME → `hinyan1016.github.io`（**DNS only/グレー雲**）／`www` 同様／blog=CNAME hatenablog.com／tools・check=CNAME hinyan1016.github.io／apex TXT=google-site-verification。
- 旧「Redirect Root to Blog」リダイレクトルールは**Disabled**（削除せず・可逆）。
- Pages custom domain は `gh api -X PUT repos/hinyan1016/portal/pages -f cname=ichisouzo-lab.com` で設定済（Actions方式はCNAMEファイルだけだと未設定のまま）。Enforce HTTPS 有効。
- 罠: Cloudflareダッシュボードは自動操作だと初回ロードで固まることがある（手動でウィンドウ操作すると解消）。

## 各所の相互リンク（ポータルへの戻り）
- ツール全HTMLの先頭に `id=ics-globalnav` ナビ（sw.js は v49）。
- はてな「デザイン→ヘッダ→ブログタイトル下(header-html)」にナビHTML（PC/スマホ両対応・レスポンシブテーマ）。
- YouTubeチャンネルの「リンク」欄にポータル/ブログ。

## YouTube
- チャンネルID: **UCmZ9m9j2T9isCuJpsoiY9qQ**。正しいURL=`https://www.youtube.com/channel/UCmZ9m9j2T9isCuJpsoiY9qQ`（恒久有効）。
- `@ichisouzo-lab` は**404（未取得）**。現行ハンドルは `@Hisaji_channel`。リンクは必ずチャンネルID URLを使う。

## 既知の保留・次の候補
- **検索インデックス／カテゴリ件数は corpus_cache.json(5/31)由来で6月記事未反映**（最新の記事セクションはRSSで自動なので別問題）。ユーザー選択=**C（現状維持）**。最新化したい時: `build_corpus_cache.py`(はてなWSSE・ENV_FILEに HATENA_ID/HATENA_API_KEY 必要・全記事fetch)→`build_portal.py` 再生成。
- ギャラリーの並びは**トピック名順**（新着順は未対応・要望あれば published降順に変更可）。
- `featured.json` の featured_articles は空（注目記事の手動選定は未）。
- medical-content には本プロジェクトと無関係の未コミット変更が残っている場合あり（別作業分・下書き）。本プロジェクトの成果は portal / medical-ddx-tools / medical-content(build_infographic_gallery.py) に push 済み。

## ライブURL
- ポータル: https://ichisouzo-lab.com/
- ツール: https://tools.ichisouzo-lab.com/ ／ 図解集: https://tools.ichisouzo-lab.com/infographics-gallery/
- 症状チェック: https://check.ichisouzo-lab.com/ ／ ブログ: https://blog.ichisouzo-lab.com/
- YouTube: https://www.youtube.com/channel/UCmZ9m9j2T9isCuJpsoiY9qQ
