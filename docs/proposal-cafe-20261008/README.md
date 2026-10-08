# カフェ版の試作（2026-10-08）

先生の依頼:「イメージとしては、安心できるカフェのようなイメージで、ビジュアル的にも改善させるバージョンもお願いします。CodexのMCPも適宜つかって、画像、挿絵もいれていいです。」

ブランチ `cafe-visual` で作り、同日に先生の承認（トップと案内ページの両方）を得て main に統合した（0da164f）。

公開後の本番確認: ページ2つ・styles.css・挿絵8枚の11ファイルがコミットとSHA256で一致。明朝の読み込みと、幅1280/390/320pxで横はみ出し0を確認した。

## 変えたところ

- 配色（`styles.css` の末尾「カフェ版」）
  - クリーム `#faf6ef`・ラテ・エスプレッソを土台にした。
  - ブランドの深緑 `#205d51` は、ボタンと札に残した。
  - 夜のテーマは「夜のカフェ」（背景 `#1c1713`）。挿絵は少し暗くして表示する。
- 部品
  - ボタンと検索窓を丸くし、カードの角を大きくした。
  - 小見出し（eyebrow）はキャラメル色 `#8a5a32`、フッターはエスプレッソ `#2c221b`。
- 案内ページ（`guide.html`）
  - 冒頭を、文と挿絵を並べた大きなカードにした。幅900px以下では挿絵を上に置き、16:9 に切り詰める。
  - 入口カード2枚に挿絵と色を付けた（一般の方・ご家族はラテ、医療従事者・研修医はセージ）。
  - 形式の一覧を、深緑のメニューボード風にした（アイコン付き）。
  - 手順の番号を丸い札にし、編集方針はセージ色のカードにした。
- トップ（`src/index.html`）
  - 配色をそろえ、「ラボについて」の右の列に挿絵を置いた。
- `build_portal.py`
  - メニューボードの項目名（`dt`）も、明朝の文字集めに入れた。

## 挿絵（`assets/cafe/`）

Codex MCP（gpt-5.5、組み込みの image_gen）で 1536×1024 を4枚生成し、WebP に変換した。拡大して確かめ、文字・数字・ロゴが入っていないことを確認済み。

| ファイル | 置き場所 | 大きい版 | 小さい版 |
|---|---|---|---|
| guide-hero | 案内ページの冒頭 | 1200px・114KB | 720px・50KB |
| route-general | 一般の方・ご家族 | 900px・64KB | 690px・44KB |
| route-pro | 医療従事者・研修医 | 900px・65KB | 690px・45KB |
| about-cafe | トップ「ラボについて」 | 1200px・99KB | 720px・43KB |

`srcset` と `sizes` で、画面幅に合う版を読ませる。案内ページ冒頭の挿絵以外は `loading="lazy"`。

共通の画風（各プロンプトの先頭に付けた）:

> Warm, reassuring neighborhood-cafe illustration in a soft hand-painted gouache look with subtle paper grain, flat 2D shapes with gentle rounded forms. Limited warm palette: cream #F4EBDD, latte beige #E2CDB0, caramel #B98A5E, espresso brown #4A3328, sage green #8FAE8B, with deep green #205D51 as small accents. Soft natural light, gentle shadows, calm and cozy mood, uncluttered composition with breathing room. Not photorealistic, no glossy 3D render, no neon, no lens flare, no harsh contrast. Absolutely no text, letters, numbers, symbols, logos or signage anywhere; books, screens, papers, cups and walls are blank or show only simple abstract marks.

- guide-hero: A quiet window seat in a cozy cafe. On a light wooden table: a latte with simple leaf latte art and a soft curl of steam, an open notebook with a soft line doodle of a brain (no writing), a tablet whose screen shows a gentle glowing pattern of connected dots suggesting AI, and a small potted plant. Morning sunlight through the window, hanging plants, and a softly blurred bookshelf in the background. No people.
- route-general: Two people sitting side by side at a cafe table: an adult and their elderly parent, looking at a tablet together and smiling gently, with a cup of tea and a cup of coffee in front of them. Relaxed, warm and reassuring atmosphere. Simple stylized faces with friendly expressions, natural hands with five fingers, casual clothes in cream, sage and caramel tones. A window and plants in the background.
- route-pro: A young clinician with a stethoscope around the neck, wearing a simple light-colored shirt, sitting at a cafe counter with a cup of coffee and calmly reviewing notes on a tablet; a few blank index cards and a small stack of plain books beside them. Focused yet relaxed and trustworthy. Simple stylized face, natural hands with five fingers. Cafe shelves with plants softly in the background.
- about-cafe: A cozy cafe counter in warm late-afternoon light. An open laptop gives off soft floating light particles that form a gentle constellation of connected dots above it, as if knowledge is being shared with the whole room. Beside it: a latte, a small stack of plain books and a potted plant. Warm pendant lamps overhead, a wooden counter, and a few empty cafe chairs that invite people to sit down. Hopeful, welcoming and calm. No people.

## 確かめたこと

- テストはすべて合格した。内訳は、`pytest` 71件、`tests/browser_redesign.py`、`tests/browser_runtime.py`、`node --check app.js`。
- 画面幅は 1280・390・320px、テーマは昼と夜の組み合わせで見た。トップと案内ページのどちらも、横はみ出しは0、壊れた画像は0。
- 幅 768・900・1024px でも、案内ページの見出しは2行に収まり、はみ出しは0。
- `styles.css` は 38,844 → 44,754 バイト（gzip では 9,192 → 10,763）。トップの挿絵は、スクロールして近づいたときだけ読み込む。

## 戻し方

このコミットを `git revert` する。`assets/cafe/` も一緒に消える。
