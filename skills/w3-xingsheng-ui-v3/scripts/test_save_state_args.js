#!/usr/bin/env node
const assert = require('assert');
const mod = require('./save_storage_state');

const args = mod.parseArgs([
  'node',
  'save_storage_state.js',
  '--url', 'https://xinsheng.huawei.com/next/index/#/home',
  '--out', './storageState.json',
  '--headful',
]);

assert.equal(args.url, 'https://xinsheng.huawei.com/next/index/#/home');
assert.equal(args.out, './storageState.json');
assert.equal(args.headful, true);

console.log('ok');
