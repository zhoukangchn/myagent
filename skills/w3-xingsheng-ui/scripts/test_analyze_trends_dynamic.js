#!/usr/bin/env node
const assert = require('assert');
const mod = require('./analyze_trends');

const rows = [
  { title: '鸿蒙开发训练营报名开启', replies: '12', views: '120' },
  { title: '鸿蒙应用实战分享会', replies: '8', views: '88' },
  { title: '篮球比赛周末组队', replies: '18', views: '160' },
  { title: '篮球训练和体能恢复经验', replies: '5', views: '90' },
  { title: '心理减压工作坊开放预约', replies: '9', views: '70' },
];

const result = mod.analyzeRows(rows);
assert.ok(Array.isArray(result.topCategories));
assert.ok(result.topCategories.length > 0);

const labels = result.topCategories.map(([k]) => k).join(' ');
assert.ok(labels.includes('鸿蒙') || labels.includes('篮球') || labels.includes('心理'));

const report = mod.buildReport(rows, result);
assert.ok(report.includes('趋势结论'));
assert.ok(!report.includes('社区从“发帖”转向“组局”')); // old hard-coded sentence

console.log('ok');
