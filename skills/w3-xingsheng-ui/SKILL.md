---
name: w3-xingsheng-ui
description: Scrape and summarize public list/detail content from Huawei Xinsheng (xinsheng.huawei.com) using Playwright in headed mode while preferring local installed Chrome/Edge (especially for Windows intranet environments where browser downloads are blocked). Use when user needs visible browser automation, manual login/captcha handling, persistent local profile reuse, pagination, detail extraction, and JSON/CSV export.
---

# w3-xingsheng-ui

Use this skill to collect structured data from Xinsheng pages with a visible browser (not headless by default).


## Deprecation Notice

This skill is deprecated. Use `w3-xingsheng-ui-v3` for new tasks.

Reasons:
- Windows intranet local-browser flow is actively maintained in v3.
- Login-state guidance and troubleshooting are maintained in v3.
- Trend analysis improvements continue in v3.

## Quick Start (Windows Intranet / Local Chrome First)

Run from the skill directory:

```bash
npm i -D playwright
node scripts/scrape_xinsheng_ui.js \
  --url "https://xinsheng.huawei.com/next/index/#/list?id=713534611705233414&cid=&flag=all&sort=&type=all&p=1" \
  --browser-channel chrome \
  --pages 2 \
  --out outputs/xinsheng.json
```

> No `playwright install` is required when using local Chrome/Edge.

For CSV output:

```bash
node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --pages 2 --out outputs/xinsheng.csv --format csv
```

## Workflow

1. Install Playwright package only (`npm i -D playwright`).
2. Start from a list URL (`#/list?...`).
3. Launch visible browser with persistent profile (`.browser-profile/` by default), preferring local Chrome/Edge (`channel=chrome/msedge` or explicit executable path).
4. Extract post cards (title/link/author/time/views/replies).
5. Paginate with the “下一页” control until target pages are reached.
6. Optionally fetch details (`--detail`) to pull article text.
7. Export JSON or CSV.

## Commands

- List-only extraction:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --pages 3 --out outputs/posts.json`
- List + detail text:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --pages 2 --detail --out outputs/posts.json`
- Limit records:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --pages 5 --max-items 120 --out outputs/posts.csv --format csv`
- Reuse local persistent profile:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --user-data-dir ./.browser-profile --out outputs/posts.json`
- Windows/local Chrome explicit channel:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --out outputs/posts.json`
- Windows/local Chrome explicit path:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-path "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --out outputs/posts.json`
- Force headless (optional fallback):
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --headless --out outputs/posts.json`
- Start visible login and save storage state:
  - `node scripts/save_storage_state_ui.js --url "https://xinsheng.huawei.com/next/index/#/home" --browser-channel chrome --out ./storageState.json`
- Reuse storage state:
  - `node scripts/scrape_xinsheng_ui.js --url "<list-url>" --browser-channel chrome --storage-state ./storageState.json --out outputs/posts.json`

## Login State & How to Decide Whether Login Is Required

Use this checklist after opening the list URL:

1. If the page redirects to login, or shows login/scan/verification UI, treat as `LOGIN_REQUIRED`.
2. If the page stays on list URL and post cards are visible, treat as `LOGIN_OK`.
3. If no cards are visible and page shows permission/login hints, treat as `LOGIN_REQUIRED`.

Recommended sequence on Windows intranet:

```bash
# Step 1: login and keep same profile directory
node scripts/save_storage_state_ui.js \
  --url "https://xinsheng.huawei.com/next/index/#/home" \
  --browser-channel chrome \
  --user-data-dir "D:\\xinsheng-profile" \
  --timeout-ms 300000 \
  --out ./storageState.json

# Step 2: scrape with the exact same profile directory
node scripts/scrape_xinsheng_ui.js \
  --url "<list-url>" \
  --browser-channel chrome \
  --user-data-dir "D:\\xinsheng-profile" \
  --out outputs/posts.json
```

Troubleshooting if login is lost:

- Keep `--user-data-dir` identical between login and scrape runs (prefer absolute path).
- Avoid mixing profile mode and `--storage-state` until profile reuse is verified.
- Close all manual Chrome windows using the same profile before running script.
- If company policy clears session frequently, re-login with Step 1.

## Notes

- Target only public content and respect site terms/policies.
- Defaults to headed mode (`headless=false`) so you can observe and manually complete login/captcha.
- If page structure changes, update selectors in `scripts/scrape_xinsheng_ui.js`.
- If navigation is slow, increase `--wait-ms` and `--timeout-ms`.
