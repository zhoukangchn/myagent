#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

function parseArgs(argv) {
  const out = {
    url: 'https://xinsheng.huawei.com/next/index/#/home',
    out: './storageState.json',
    headful: false,
    timeoutMs: 300000,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const n = argv[i + 1];
    if (a === '--url') out.url = n, i++;
    else if (a === '--out') out.out = n, i++;
    else if (a === '--headful') out.headful = true;
    else if (a === '--timeout-ms') out.timeoutMs = Number(n || 300000), i++;
  }
  return out;
}

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

async function main(argv = process.argv) {
  const args = parseArgs(argv);
  const browser = await chromium.launch({ headless: !args.headful });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(args.url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    console.log('Please complete login in the browser window.');
    console.log(`Waiting up to ${Math.floor(args.timeoutMs / 1000)}s ...`);

    await page.waitForTimeout(args.timeoutMs);

    ensureDir(args.out);
    await context.storageState({ path: args.out });
    console.log(`Saved storage state to: ${args.out}`);
  } finally {
    await context.close();
    await browser.close();
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  parseArgs,
  main,
};
