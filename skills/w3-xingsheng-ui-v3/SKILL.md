---
name: w3-xingsheng-ui-v3
description: Scrape and summarize public Xinsheng (xinsheng.huawei.com) list content in Windows intranet environments using Playwright headed mode with local Chrome/Edge (no browser download). Use for non-login runs that output JSON and a markdown trend report directly (no CSV workflow).
---

# w3-xingsheng-ui-v3

Use this v3 skill for a **simple non-login flow** on Windows: local browser -> JSON data -> markdown trend report.

## Quick Start (Windows / Local Chrome / No Login)

Run from skill directory:

```bash
npm i -D playwright
node scripts/scrape_xinsheng_ui.js \
  --url "https://xinsheng.huawei.com/next/index/#/list?id=713534611705233414&cid=&flag=all&sort=&type=all&p=1" \
  --browser-channel chrome \
  --pages 1 \
  --out outputs/posts.json

node scripts/analyze_trends.js \
  --input outputs/posts.json \
  --out outputs/trend-report.md
```

## Workflow

1. Install Playwright package only (`npm i -D playwright`).
2. Use local Chrome (`--browser-channel chrome`) in headed mode.
3. Scrape list page(s) to JSON.
4. Generate markdown trend report from JSON.

## Required Command Style

- Always include `--browser-channel chrome` on Windows.
- Always output JSON (`--out ...json`).
- Do not use CSV commands in this skill variant.
- Default to non-login list scraping.

## Commands

- Basic non-login scrape:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --pages 1 --out outputs/posts.json`
- Generate trend report:
  - `node scripts/analyze_trends.js --input outputs/posts.json --out outputs/trend-report.md`
- Optional details extraction:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --pages 1 --detail --out outputs/posts-detail.json`

## Notes

- This v3 document intentionally excludes login/storage-state instructions.
- This v3 document intentionally excludes CSV workflow.
- If local Chrome path is required by policy, use `--browser-path "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"`.
- If navigation is slow, increase `--wait-ms` and `--timeout-ms`.
