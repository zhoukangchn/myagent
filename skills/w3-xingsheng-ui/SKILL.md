---
name: w3-xingsheng-ui
description: Scrape and summarize public list/detail content from Huawei Xinsheng (xinsheng.huawei.com) using Playwright with a visible browser window (headed mode, real UI). Use when user wants non-headless scraping, needs to watch/operate login manually, reuse persistent local browser profile, paginate list pages, extract title/author/time/views/replies, pull detail text, or export JSON/CSV.
---

# w3-xingsheng-ui

Use this skill to collect structured data from Xinsheng pages with a visible browser (not headless by default).

## Quick Start

Run from the skill directory:

```bash
npm i -D playwright
npx playwright install chromium
node scripts/scrape_xinsheng_ui.js \
  --url "https://xinsheng.huawei.com/next/index/#/list?id=713534611705233414&cid=&flag=all&sort=&type=all&p=1" \
  --pages 2 \
  --out outputs/xinsheng.json
```

For CSV output:

```bash
node scripts/scrape_xinsheng_ui.js --url "<list-url>" --pages 2 --out outputs/xinsheng.csv --format csv
```

## Workflow

1. Install Playwright + Chromium.
2. Start from a list URL (`#/list?...`).
3. Launch visible browser with persistent profile (`.browser-profile/` by default).
4. Extract post cards (title/link/author/time/views/replies).
5. Paginate with the “下一页” control until target pages are reached.
6. Optionally fetch details (`--detail`) to pull article text.
7. Export JSON or CSV.

## Commands

- List-only extraction:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --pages 3 --out outputs/posts.json`
- List + detail text:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --pages 2 --detail --out outputs/posts.json`
- Limit records:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --pages 5 --max-items 120 --out outputs/posts.csv --format csv`
- Reuse local persistent profile:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --user-data-dir ./.browser-profile --out outputs/posts.json`
- Force headless (optional fallback):
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --headless --out outputs/posts.json`
- Start visible login and save storage state:
  - `node scripts/save_storage_state_ui.js --url "https://xinsheng.huawei.com/next/index/#/home" --out ./storageState.json`
- Reuse storage state:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --storage-state ./storageState.json --out outputs/posts.json`

## Notes

- Target only public content and respect site terms/policies.
- Defaults to headed mode (`headless=false`) so you can observe and manually complete login/captcha.
- If page structure changes, update selectors in `scripts/scrape_xinsheng_ui.js`.
- If navigation is slow, increase `--wait-ms` and `--timeout-ms`.
