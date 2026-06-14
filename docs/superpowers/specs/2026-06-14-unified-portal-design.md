# 統合ポータル（医知創造ラボ）設計書

- 作成日: 2026-06-14
- 対象: ブランド「医知創造ラボ」の正面玄関となる統合ポータルサイト
- 設置先（最終）: apex `ichisouzo-lab.com`（新規 GitHub Pages リポジトリ）

---

## 1. 目的・背景

ブログ記事（620本超）・診断ツール・インフォグラフィック・スライド・YouTube が
サブドメインごとにバラバラに存在し、横断的な「入口」が無い。

各機能へ送り出す **統合ポータル（玄関ページ）** を作り、訪問者が目的の
コンテンツに最短でたどり着けるようにする。記事はカテゴリ単位で束ね、はてなの
自動カテゴリページへリンクすることで **更新の手間をかけずに中身を最新化** する。

### ユーザーの決定事項
- 主目的: **統合ポータル**（ブログ＋ツール＋YouTube を一望できる玄関）
- 置き場所: **apex `ichisouzo-lab.com`**
- 記事の見せ方: **カテゴリページへのリンク中心**（はてな自動カテゴリページを活用）＋注目記事少数
- 進め方: **ポータルを先に作り、DNS 切り替えは最後**（完成後に改めて判断）

---

## 2. 現状のドメイン構成（調査結果 2026-06-14）

| ホスト | 種別 | 向き先 | Proxy |
|---|---|---|---|
| `ichisouzo-lab.com`（apex） | A | `192.0.2.1`（ダミー） | 🟠 Proxied |
| `ichisouzo-lab.com` | TXT | `google-site-verification…` | DNS only |
| `blog.ichisouzo-lab.com` | CNAME | `hatenablog.com` | DNS only |
| `tools.ichisouzo-lab.com` | CNAME | `hinyan1016.github.io` | DNS only |
| `check.ichisouzo-lab.com` | CNAME | `hinyan1016.github.io` | DNS only |

- DNS は **Cloudflare** 管理（アカウント `Hinyan1016@gmail.com`、Zone `ichisouzo-lab.com`、Free プラン）。
- **重要**: apex は未使用ではなく、Cloudflare Redirect Rule **「Redirect Root to Blog」(Active)** により
  `ichisouzo-lab.com → 301 → ブログ` へ転送されている。`A 192.0.2.1 (Proxied)` はこの転送用のダミー。
- apex をポータルにするには、この転送の無効化と apex A レコードの差し替えが必要（→ §7、最終工程で実施）。

---

## 3. サイト構成（apex の 1 枚もの `index.html`）

`tools.ichisouzo-lab.com/index.html` のカード型 UI を踏襲。上から:

1. **ヒーロー** — ブランド名「医知創造ラボ」＋一言説明＋主要3導線（記事を探す／診断ツール／YouTube）
2. **ブログを探す** — カテゴリカード。各 **はてな自動カテゴリページ** へリンク（中身は自動最新化）。3 グループ:
   - 読者別: `医師向け` `初期研修医` `一般向け`
   - テーマ別（厳選 ~12）: `脳神経内科` `薬` `医療安全` `てんかん` `脳卒中` `感染症` `栄養` `認知症` `糖尿` `頭痛` `パーキンソン病` `ガイドライン`
   - シリーズ: `その症状大丈夫` `からだの不思議` `20年の変遷シリーズ` `セルフチェック`
3. **注目・最新記事** — `inventory_v2.csv` の最新 N 件（自動）＋手動ピック数件（`featured.json`）
4. **診断ツール** — `tools.ichisouzo-lab.com` の代表ツール数個＋「全ツール一覧」へのリンク
5. **症状セルフチェック** — `check.ichisouzo-lab.com`
6. **インフォグラフィック／スライド** — `tools` 配下の一覧へ
7. **YouTube** — `https://www.youtube.com/@ichisouzo-lab`
8. **フッター** — 運営者・免責・プライバシー・各サブドメインへのリンク

### カテゴリ選定の方針
- 包括的すぎる「メタ」カテゴリ（`医学情報 546` など）は出さない。テーマが具体的なものを厳選。
- 件数はラベルに併記（例: `脳神経内科 395`）。件数は生成時に `inventory_v2.csv` から自動集計。

### はてなカテゴリURL 形式
`https://blog.ichisouzo-lab.com/archive/category/<カテゴリ名を URL エンコード>`
- 生成スクリプトでカテゴリ名を URL エンコードして組み立てる。
- ビルド時にサンプル数件へ HTTP アクセスし 200 を確認（リンク切れ防止）。

---

## 4. メンテナンス方式（データ生成）

620 記事＋日々増える前提のため **手書き HTML を避け、データから生成**する。

### 生成スクリプト `build_portal.py`
入力:
- `medical-content/blog/infographic-project/data/inventory_v2.csv`
  （列: `entry_id,title,category,published,word_count,status,reason,url`）
- `medical-ddx-tools/`（ツール `*.html`／`infographics/`／`slides/` を走査）
- `portal/featured.json`（手動の注目記事・代表ツールの上書き）
- `portal/config.json`（ブランド名・カテゴリ選定リスト・YouTube URL 等の設定）

処理:
1. `status` が公開のレコードからカテゴリ別件数を集計
2. 設定の選定カテゴリについて、件数＋はてなカテゴリURL を生成
3. 最新記事を `published` 降順で N 件抽出
4. `medical-ddx-tools/` を走査しツール／インフォ／スライド一覧を反映
5. テンプレートに流し込み `portal/index.html` を **丸ごと生成**

運用:
- 記事を増やしたら **再実行 → commit → push** するだけで件数・新カテゴリ・新ツールが反映。
- 注目記事・代表ツールの「人の手で選ぶ」部分のみ `featured.json` で管理。

### コーディング規約（既存資産に合わせる）
- 単一 `index.html`（CSS/JS 内包、外部依存なし）。
- ハウススタイル: `--navy:#1B3A5C` `--blue:#2C5AA0` `--light-blue:#E8F0FE` ＋差し色コーラル `#FF7A59`。
  フォント `游ゴシック, Yu Gothic, Segoe UI`。カード UI。`max-width` はセクションが多いため ~960px。
- レスポンシブ（スマホ 1 カラム）。JS は最小限（カテゴリ検索/フィルタ程度）。
- 日本語 UI・日本語コメント。

---

## 5. リポジトリ／デプロイ

- 新規リポジトリ **`hinyan1016/portal`**（仮名）。ローカルは `portal/`。
- GitHub Pages を `main` から配信。
- **ビルド段階では `CNAME` ファイルを置かない** → プレビューは `https://hinyan1016.github.io/portal/`。
- 完成・確認後に `CNAME = ichisouzo-lab.com` を追加し、DNS を切り替える（§7）。

---

## 6. プレビュー／検証

- ローカルで `index.html` を開く or 簡易サーバで確認。
- push 後 `https://hinyan1016.github.io/portal/` を確認。
- チェック項目: 主要カテゴリリンクが 200／各サブドメイン導線が正しい／スマホ 1 カラム表示／
  YouTube・ツール・症状チェックの外部リンクが正しい。

---

## 7. DNS 切り替え（最終工程・ユーザー判断後に実施）

ポータル完成後に、Cloudflare で以下を実施（**いずれも可逆**）:

1. Redirect Rule **「Redirect Root to Blog」を無効化（または削除）**。
2. apex `A 192.0.2.1 (Proxied)` を削除し、GitHub Pages の **A ×4 / AAAA ×4 を DNS only（グレー雲）** で追加。
   - A: `185.199.108.153` `185.199.109.153` `185.199.110.153` `185.199.111.153`
   - AAAA: `2606:50c0:8000::153` `2606:50c0:8001::153` `2606:50c0:8002::153` `2606:50c0:8003::153`
3. `www` CNAME → `hinyan1016.github.io`（DNS only）を追加。
4. GitHub Settings → Pages でドメイン検証 TXT（`_github-pages-challenge-hinyan1016`）を Cloudflare に追加（推奨）。
5. リポジトリに `CNAME = ichisouzo-lab.com` を追加、`Enforce HTTPS` を有効化。
6. 既存の `blog` `tools` `check` `TXT(google-site-verification)` は **変更しない**。

注意:
- グレー雲（DNS only）必須。オレンジ雲だと GitHub の証明書発行に失敗する。
- どうしてもオレンジ雲にする場合のみ SSL/TLS を **Full**（**Flexible 禁止**＝リダイレクトループ）。

---

## 8. スコープ外（YAGNI）

- 全 620 記事の自動列挙ページ（今回はカテゴリリンク中心）。将来必要なら別途。
- ブログ記事側からポータルへの相互リンク張り戻し（任意・後日）。
- 多言語化・検索エンジン内部の高度な SEO 施策（基本的な内部リンクのみ）。
- メール（MX/SPF/DKIM）設定（今回の対象外）。

---

## 9. 受け入れ基準

- apex 用 `index.html` が生成スクリプトから再現可能に生成できる。
- 主要カテゴリカードがはてな自動カテゴリページ（HTTP 200）へ正しくリンクする。
- ツール／症状チェック／インフォ／スライド／YouTube への導線が正しい。
- スマホ／PC でレイアウトが崩れない。
- DNS 未切替の状態で `hinyan1016.github.io/portal/` でプレビューできる。
