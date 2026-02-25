#!/usr/bin/env node
const assert = require('assert');
const mod = require('./scrape_xinsheng');

const args = mod.parseArgs([
  'node',
  'scrape_xinsheng.js',
  '--url', 'https://example.com',
  '--out', 'out.json',
  '--cookie', 'a=1; b=2',
  '--cookie-file', './cookies.txt',
  '--storage-state', './state.json',
]);

assert.equal(args.cookie, 'a=1; b=2');
assert.equal(args.cookieFile, './cookies.txt');
assert.equal(args.storageState, './state.json');

console.log('ok');
