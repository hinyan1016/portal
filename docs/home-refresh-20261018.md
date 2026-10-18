# トップページ掲載内容の公開確認（2026-10-18）

## 新着記事・解説動画
公開RSSの日時と各記事ページHTTP 200、YouTube oEmbed HTTP 200・タイトルで確認。

| 記事 | 公開日（日本時間） | 対応動画 |
|---|---|---|
| [LGSの診断](https://blog.ichisouzo-lab.com/entry/2026/10/18/093938) | 2026-10-18 09:39:38 | [LGSの診断](https://www.youtube.com/watch?v=uO4F4mw6W4g) |
| [LGSの治療](https://blog.ichisouzo-lab.com/entry/2026/10/18/091939) | 2026-10-18 09:19:39 | [LGSの治療](https://www.youtube.com/watch?v=2_UyvUVRrro) |
| [成人フェンフルラミン](https://blog.ichisouzo-lab.com/entry/2026/10/16/234415) | 2026-10-16 23:44:15 | [成人フェンフルラミン](https://www.youtube.com/watch?v=PMxcp6uwnt8) |

動画の公開日は未取得のため表示しない。記事カードの日時は記事公開日。
旧フェンフルラミン記事（2025/09/06/083747）の改訂や制作中の神経伝導検査・針筋電図動画は掲載対象にしていない。

## ツール
- [日常生活自立度判定支援](https://tools.ichisouzo-lab.com/daily_living_independence.html): HTTP 200、作成日2026-10-15。
- [MNIアトラス](https://tools.ichisouzo-lab.com/vascular-territory-atlas.html): HTTP 200。既存の10/12改訂の根拠は共有台帳・証跡を維持。
- [不眠の配布資料](https://tools.ichisouzo-lab.com/handouts/insomnia-lifestyle-guidance/): HTTP 200、「作成：2026年10月」。日付は推定しない。
- GitHub releases/latestでオフライン版最新は `offline-v1.3`（2026-10-13）と確認。既存案内を保持。

## 運用・復旧
変更前はmain `ee76ab2`。対象ファイルのバイト単位バックアップとSHA-256は作業環境 `refresh-20261018/backup/` と `backup-sha256.json` に保存。
この変更だけ戻す場合は本更新コミットを `git revert <commit>` して通常のPages公開を行う。後続の自動カタログ更新は戻さない。
共有台帳・ウィジェット・コラム・アプリJavaScriptは変更対象外。ブログ側の設定は変更しない。
