# 統合ポータル（医知創造ラボ）

apex `ichisouzo-lab.com` 用のポータル `index.html` を生成する。

## 再生成

```bash
/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe build_portal.py
```

- データ源: `../medical-content/blog/seo-improvement/corpus_cache.json`
- ツール走査: `../medical-ddx-tools/`
- 手動調整: `featured.json`（注目記事・代表ツール）、`config.json`（カテゴリ選定・各URL）

## テスト

```bash
/c/Users/jsber/AppData/Local/Programs/Python/Python313/python.exe -m pytest tests -q
```

## デプロイ（最終工程・別途）

`docs/superpowers/specs/2026-06-14-unified-portal-design.md` の §7 参照。
完成後に `CNAME = ichisouzo-lab.com` を追加し、Cloudflare で apex リダイレクト無効化＋
A レコード差し替えを行う。**ビルド段階では CNAME を置かない**（プレビューは
`https://hinyan1016.github.io/portal/`）。
