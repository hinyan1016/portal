# トップのAI・知識ブーストGIF（2026-11-10）

先生の依頼に基づき、緑背景で本から神経が伸びる旧画像を、明るい本・AIチップ・上向きの矢印へ差し替えた。HyperFramesは使用していない。

Codexの組み込み画像生成でイラストと透過チップを作成し、Pillowで位置と光の周期運動を合成した。外部の動画生成サービスや有料音声は使用していない。

- 公開画像: `assets/hero-ai-knowledge.gif`（576×384、100フレーム、20fps、5秒、無限ループ、567,443 bytes）
- 動きを抑える設定では `assets/hero-ai-knowledge.webp` を表示。
- 正本の `src/index.html` と生成済みの `index.html` を更新。旧画像は復元用に保持。
- 再生成: `PYTHONIOENCODING=utf-8 python scripts/build_hero_ai_gif.py`
- 公開前検査: pytest 135件、`browser_redesign.py`、画像専用ブラウザー検査、公開用配置、JavaScript構文、差分検査を通過。
- 画像専用検査は1440/768/390/320pxで読み込み・横はみ出しなしを確認。再生開始から6秒後と7.25秒後の画像が変化すること、動きを抑える設定で静止画になることを確認。原寸の6時点一覧とPC・スマートフォン画面を目視確認。

## 画像生成プロンプト

原画: Clean premium softly rounded 3D editorial illustration conveying “AI boosts knowledge”, landscape 3:2, warm ivory background #faf6ef. A large open cream-paper book with a deep teal cover; a separate friendly emerald rounded microchip above it labeled only “AI”; a golden upward arrow beside the book toward the chip and small gold sparkles. Soft studio lighting, clear silhouettes, readable at 105px. No person, brain, nerves, branches, roots, tentacles, organic tendrils, green background or clutter.

本のレイヤー: Remove only the microchip and four sparkles from the original illustration, fill with the existing warm cream background, preserve book, arrow, light, shadows, positions, colours and framing exactly.

チップのレイヤー: Extract only the existing AI microchip with gold pins and ivory letters as a transparent cutout; preserve the original appearance, proportions, orientation, size, location and framing; all other pixels transparent.

原画・本のレイヤー・チップのレイヤーはこのフォルダーに保存。公開用配置には制作記録や原画を含めず、完成GIF・静止画だけを追加する。
