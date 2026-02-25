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
    browserChannel: '',
    browserPath: '',
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const n = argv[i + 1];
    if (a === '--url') out.url = n, i++;
    else if (a === '--out') out.out = n, i++;
    else if (a === '--timeout-ms') out.timeoutMs = Number(n || 300000), i++;
    else if (a === '--headless') out.headless = true;
    else if (a === '--user-data-dir') out.userDataDir = path.resolve(n || '.browser-profile'), i++;
    else if (a === '--browser-channel') out.browserChannel = n || '', i++;
    else if (a === '--browser-path') out.browserPath = n || '', i++;
  }
  return out;
}

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function buildLaunchCandidates(args) {
  const base = { headless: args.headless };

  if (args.browserPath) return [{ ...base, executablePath: args.browserPath }];
  if (args.browserChannel) return [{ ...base, channel: args.browserChannel }];

  if (process.platform === 'win32') {
    return [
      { ...base, channel: 'chrome' },
      { ...base, executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe' },
      { ...base, executablePath: 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe' },
      { ...base, channel: 'msedge' },
      { ...base, executablePath: 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe' },
      base,
    ];
  }

  return [
    { ...base, channel: 'chrome' },
    { ...base, executablePath: '/usr/bin/google-chrome-stable' },
    { ...base, executablePath: '/usr/bin/google-chrome' },
    { ...base, executablePath: '/usr/bin/chromium' },
    { ...base, executablePath: '/usr/bin/chromium-browser' },
    base,
  ];
}

async function launchContext(args) {
  fs.mkdirSync(args.userDataDir, { recursive: true });
  const candidates = buildLaunchCandidates(args);
  let lastError = null;

  for (const opt of candidates) {
    try {
      const context = await chromium.launchPersistentContext(args.userDataDir, opt);
      const mode = opt.channel ? `channel=${opt.channel}` : (opt.executablePath ? `path=${opt.executablePath}` : 'playwright-default');
      console.log(`[browser] launched with ${mode}`);
      return context;
    } catch (e) {
      lastError = e;
    }
  }

  throw lastError || new Error('Failed to launch browser');
}

async function main(argv = process.argv) {
  const args = parseArgs(argv);
  const context = await launchContext(args);
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
  buildLaunchCandidates,
  launchContext,
  main,
};
