#!/usr/bin/env node
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { resolveCookie } = require('./scrape_xinsheng');

const fp = path.join(__dirname, '.tmp-cookie.txt');
fs.writeFileSync(fp, 'foo=bar; sid=123', 'utf8');

const cookie = resolveCookie({ cookie: '', cookieFile: fp });
assert.equal(cookie, 'foo=bar; sid=123');

fs.unlinkSync(fp);
console.log('ok');
