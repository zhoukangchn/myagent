#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

function parseArgs(argv) {
  const out = {
    pages: 1,
    detail: false,
    format: 'json',
    waitMs: 2500,
    maxItems: 0,
    timeoutMs: 90000,
    cookie: '',
    cookieFile: '',
    storageState: '',
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const n = argv[i + 1];
    if (a === '--url') out.url = n, i++;
    else if (a === '--pages') out.pages = Number(n || 1), i++;
    else if (a === '--out') out.out = n, i++;
    else if (a === '--detail') out.detail = true;
    else if (a === '--format') out.format = (n || 'json').toLowerCase(), i++;
    else if (a === '--wait-ms') out.waitMs = Number(n || 2500), i++;
    else if (a === '--max-items') out.maxItems = Number(n || 0), i++;
    else if (a === '--timeout-ms') out.timeoutMs = Number(n || 90000), i++;
    else if (a === '--cookie') out.cookie = n || '', i++;
    else if (a === '--cookie-file') out.cookieFile = n || '', i++;
    else if (a === '--storage-state') out.storageState = n || '', i++;
  }
  return out;
}

function ensureDir(filePath) {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
}

function toCsv(rows) {
  const headers = ['title', 'detailUrl', 'author', 'publishTime', 'latestReply', 'views', 'replies', 'content'];
  const esc = (v) => {
    const s = String(v ?? '');
    if (s.includes('"') || s.includes(',') || s.includes('\n')) {
      return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  };
  return [headers.join(','), ...rows.map(r => headers.map(h => esc(r[h])).join(','))].join('\n');
}

function resolveCookie(args) {
  if (args.cookie && args.cookie.trim()) return args.cookie.trim();
  if (args.cookieFile) {
    const raw = fs.readFileSync(args.cookieFile, 'utf8').trim();
    if (raw) return raw;
  }
  return '';
}

async function createContext(browser, args) {
  const cookie = resolveCookie(args);
  const contextOptions = {};

  if (args.storageState) contextOptions.storageState = args.storageState;
  if (cookie) contextOptions.extraHTTPHeaders = { Cookie: cookie };

  return browser.newContext(contextOptions);
}

async function extractList(page) {
  return page.evaluate(() => {
    const parseStats = (root) => {
      const nums = Array.from(root.querySelectorAll('*'))
        .map(x => (x.textContent || '').trim())
        .filter(t => /^(\d+(\.\d+)?万?|\d+)$/.test(t));
      return {
        views: nums[0] || '',
        replies: nums[1] || '',
      };
    };

    const links = Array.from(document.querySelectorAll('a[href*="/next/detail/#/detail?uuid="]'));
    const seen = new Set();
    const posts = [];

    for (const a of links) {
      const detailUrl = a.href;
      if (!detailUrl || seen.has(detailUrl)) continue;
      const title = (a.textContent || '').trim();
      if (!title) continue;
      seen.add(detailUrl);

      const card = a.closest('div') || document.body;
      const text = (card.textContent || '').replace(/\s+/g, ' ').trim();
      const dateMatch = text.match(/(\d{4}-\d{2}-\d{2}|\d+小时前|\d+天前)/g) || [];
      const stats = parseStats(card);

      const authorMatch = text.match(/([\u4e00-\u9fa5A-Za-z0-9*]{2,20})(\s*\|)?\s*(\d{4}-\d{2}-\d{2}|\d+小时前|\d+天前)/);
      const author = authorMatch ? authorMatch[1] : '';

      posts.push({
        title,
        detailUrl,
        author,
        publishTime: dateMatch[0] || '',
        latestReply: dateMatch[1] || '',
        views: stats.views,
        replies: stats.replies,
      });
    }
    return posts;
  });
}

async function extractDetail(page, url, timeoutMs) {
  const p = await page.context().newPage();
  try {
    await p.goto(url, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
    await p.waitForTimeout(1200);
    const text = await p.evaluate(() => {
      const candidates = ['article', '[class*="detail"]', '[class*="content"]', '.ql-editor', '.markdown-body'];
      let best = '';
      for (const sel of candidates) {
        const nodes = Array.from(document.querySelectorAll(sel));
        for (const node of nodes) {
          const t = (node.textContent || '').replace(/\s+/g, ' ').trim();
          if (t.length > best.length) best = t;
        }
      }
      if (!best) best = (document.body?.textContent || '').replace(/\s+/g, ' ').trim();
      return best.slice(0, 12000);
    });
    return text;
  } catch {
    return '';
  } finally {
    await p.close();
  }
}

async function clickNext(page) {
  const next = page.locator('button:has-text("下一页")').first();
  if (await next.count() === 0) return false;
  const disabled = await next.getAttribute('disabled');
  if (disabled !== null) return false;
  await next.click();
  return true;
}

async function main(argv = process.argv) {
  const args = parseArgs(argv);
  if (!args.url || !args.out) {
    console.error('Usage: node scrape_xinsheng.js --url <list-url> --out <file> [--pages 1] [--detail] [--format json|csv] [--wait-ms 2500] [--max-items 0] [--cookie "k=v;..."] [--cookie-file cookies.txt] [--storage-state state.json]');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await createContext(browser, args);
  const page = await context.newPage();

  const all = [];
  const seen = new Set();

  try {
    await page.goto(args.url, { waitUntil: 'domcontentloaded', timeout: args.timeoutMs });

    for (let p = 1; p <= Math.max(1, args.pages); p++) {
      await page.waitForTimeout(args.waitMs);
      const rows = await extractList(page);
      for (const row of rows) {
        if (seen.has(row.detailUrl)) continue;
        seen.add(row.detailUrl);
        all.push(row);
        if (args.maxItems > 0 && all.length >= args.maxItems) break;
      }
      if (args.maxItems > 0 && all.length >= args.maxItems) break;
      if (p < args.pages) {
        const moved = await clickNext(page);
        if (!moved) break;
      }
    }

    if (args.detail) {
      for (let i = 0; i < all.length; i++) {
        all[i].content = await extractDetail(page, all[i].detailUrl, args.timeoutMs);
      }
    }

    ensureDir(args.out);
    const format = args.format || (args.out.toLowerCase().endsWith('.csv') ? 'csv' : 'json');

    if (format === 'csv') fs.writeFileSync(args.out, toCsv(all), 'utf8');
    else fs.writeFileSync(args.out, JSON.stringify(all, null, 2), 'utf8');

    console.log(`Saved ${all.length} records to ${args.out}`);
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
  resolveCookie,
  createContext,
  main,
};
