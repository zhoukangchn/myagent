#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

function parseArgs(argv) {
  const out = {
    url: 'https://xinsheng.huawei.com/next/index/#/home',
    out: './storageState.json',
    timeoutMs: 300000,
    headless: false,
    userDataDir: path.resolve('.browser-profile'),
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const n = argv[i + 1];
    if (a === '--url') out.url = n, i++;
    else if (a === '--out') out.out = n, i++;
    else if (a === '--timeout-ms') out.timeoutMs = Number(n || 300000), i++;
    else if (a === '--headless') out.headless = true;
    else if (a === '--user-data-dir') out.userDataDir = path.resolve(n || '.browser-profile'), i++;
  }
  return out;
}

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

async function main(argv = process.argv) {
  const args = parseArgs(argv);
  fs.mkdirSync(args.userDataDir, { recursive: true });

  const context = await chromium.launchPersistentContext(args.userDataDir, {
    headless: args.headless,
  });
  const page = context.pages()[0] || await context.newPage();

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
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  parseArgs,
  main,
};
