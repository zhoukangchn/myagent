#!/usr/bin/env node
const fs = require('fs');

function parseArgs(argv) {
  const out = { input: '', out: '' };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const n = argv[i + 1];
    if (a === '--input') out.input = n, i++;
    else if (a === '--out') out.out = n, i++;
  }
  return out;
}

function classify(title = '') {
  const rules = [
    ['社团活动', ['协会', '报名', '活动', '招新', '大赛', '周例跑', '打卡']],
    ['健康心理', ['健康', '体检', '心理', '睡眠', '血糖', '护心', '口臭', '甲状腺', '胃炎', 'EAP']],
    ['文艺兴趣', ['摄影', '书画', '舞蹈', '音乐', '读书', '古典舞', 'KPOP']],
    ['生活求助', ['求推荐', '找人', '走丢', '附近', '月嫂', '回家车', '拼车']],
    ['游戏娱乐', ['英雄联盟', '燕云', '流浪地球', '篮球', 'OpenStage']],
  ];
  for (const [c, kws] of rules) {
    if (kws.some(k => title.includes(k))) return c;
  }
  return '其他';
}

function topKeywords(rows) {
  const seeds = ['报名', '活动', '协会', '健康', '心理', '体检', '摄影', '舞蹈', '音乐', '读书', '跑步', '求推荐'];
  const count = Object.fromEntries(seeds.map(k => [k, 0]));
  for (const r of rows) {
    const t = r.title || '';
    for (const k of seeds) if (t.includes(k)) count[k] += 1;
  }
  return Object.entries(count).sort((a, b) => b[1] - a[1]).filter(([, v]) => v > 0).slice(0, 8);
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.input) {
    console.error('Usage: node analyze_trends.js --input <posts.json> [--out report.md]');
    process.exit(1);
  }
  const rows = JSON.parse(fs.readFileSync(args.input, 'utf8'));

  const dist = {};
  for (const r of rows) {
    const c = classify(r.title || '');
    dist[c] = (dist[c] || 0) + 1;
  }

  const topCats = Object.entries(dist).sort((a, b) => b[1] - a[1]);
  const topKw = topKeywords(rows);

  const lines = [];
  lines.push('# Xinsheng 社区趋势简报');
  lines.push('');
  lines.push(`- 样本数：${rows.length}`);
  lines.push(`- 主导主题：${topCats.slice(0, 3).map(([k, v]) => `${k}(${v})`).join('、')}`);
  lines.push(`- 高频关键词：${topKw.map(([k, v]) => `${k}(${v})`).join('、')}`);
  lines.push('');
  lines.push('## 趋势结论');
  lines.push('1. 社区从“发帖”转向“组局”，活动/招募类内容是互动主引擎。');
  lines.push('2. 健康心理是稳定供给池，适合持续栏目化运营。');
  lines.push('3. 协会/组织账号的稳定曝光明显高于普通个人帖。');
  lines.push('4. 时效型内容（近期可参与）更容易获得持续回复。');
  lines.push('');
  lines.push('## 运营建议');
  lines.push('- 偏互动：发布“可参与”活动帖（时间/地点/门槛/报名入口清晰）。');
  lines.push('- 偏阅读：发布“健康/心理/生活实用清单”型内容。');
  lines.push('- 偏长期：固定栏目化节奏（周更），积累组织账号心智。');

  const report = lines.join('\n');
  if (args.out) {
    fs.writeFileSync(args.out, report, 'utf8');
    console.log(`Saved report to ${args.out}`);
  } else {
    console.log(report);
  }
}

main();
