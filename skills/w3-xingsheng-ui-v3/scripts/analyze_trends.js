#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const out = { input: '', out: '', top: 8, config: '' };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    const n = argv[i + 1];
    if (a === '--input') out.input = n, i++;
    else if (a === '--out') out.out = n, i++;
    else if (a === '--top') out.top = Number(n || 8), i++;
    else if (a === '--config') out.config = n || '', i++;
  }
  return out;
}

const DEFAULT_STOPWORDS = new Set([
  '我们', '你们', '他们', '这个', '那个', '可以', '一起', '分享', '求助', '活动', '报名', '通知', '公告',
  '发布', '关于', '今天', '明天', '周末', '如何', '一个', '欢迎', '参加', '开始', '线上', '线下', '相关',
  '经验', '交流', '讨论', '大家', '组织', '协会', '社区', '公司', '内部', '最新', '请问', '有人', '请教',
  '动报', '名帖', '已结', '结束', '已结束'
]);

function loadConfig(configPath = '') {
  const fallback = path.resolve(__dirname, '../references/topic-config.json');
  const p = configPath ? path.resolve(configPath) : fallback;
  if (!fs.existsSync(p)) return { stopwords: [] };
  try {
    const cfg = JSON.parse(fs.readFileSync(p, 'utf8'));
    return { stopwords: Array.isArray(cfg.stopwords) ? cfg.stopwords : [] };
  } catch {
    return { stopwords: [] };
  }
}

function cleanTitle(text = '') {
  return String(text)
    .replace(/【[^】]*】/g, ' ')
    .replace(/\[[^\]]*\]/g, ' ')
    .replace(/\([^)]*\)/g, ' ')
    .replace(/[（][^）]*[）]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function stripStopwords(text, stopwords) {
  let t = text;
  for (const w of stopwords) t = t.split(w).join(' ');
  return t.replace(/\s+/g, ' ').trim();
}

function toBigrams(text = '') {
  const s = text.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '');
  if (s.length <= 1) return new Set([s]);
  const out = new Set();
  for (let i = 0; i < s.length - 1; i++) out.add(s.slice(i, i + 2));
  return out;
}

function jaccard(a, b) {
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  const uni = a.size + b.size - inter;
  return uni ? inter / uni : 0;
}

function toNumber(v) {
  if (typeof v === 'number') return v;
  const s = String(v ?? '').trim();
  if (!s) return 0;
  if (s.endsWith('万')) return Number(s.replace('万', '')) * 10000;
  const n = Number(s.replace(/,/g, ''));
  return Number.isFinite(n) ? n : 0;
}

function labelFromTitle(title, stopwords) {
  const t = stripStopwords(cleanTitle(title), stopwords).replace(/[，。！？,.!?]/g, '');
  if (!t) return '其他';
  return t.slice(0, 8);
}

function tokenizeTitle(title = '', stopwords = DEFAULT_STOPWORDS) {
  // kept for backward compatibility in tests
  const t = stripStopwords(cleanTitle(title), stopwords);
  return [...toBigrams(t)];
}

function analyzeRows(rows, topN = 8, cfg = { stopwords: [] }) {
  const stopwords = new Set([...DEFAULT_STOPWORDS, ...(cfg.stopwords || [])]);

  const clusters = [];
  for (const r of rows) {
    const title = cleanTitle(r.title || '');
    const sig = toBigrams(stripStopwords(title, stopwords));
    if (!title || sig.size === 0) {
      clusters.push({ items: [r], sig });
      continue;
    }

    let best = -1;
    let bestSim = 0;
    for (let i = 0; i < clusters.length; i++) {
      const sim = jaccard(sig, clusters[i].sig);
      if (sim > bestSim) {
        bestSim = sim;
        best = i;
      }
    }

    if (best >= 0 && bestSim >= 0.35) {
      clusters[best].items.push(r);
      // update signature as union
      for (const x of sig) clusters[best].sig.add(x);
    } else {
      clusters.push({ items: [r], sig });
    }
  }

  const sorted = clusters.sort((a, b) => b.items.length - a.items.length);
  const top = sorted.slice(0, topN).map(c => {
    const seedTitle = c.items[0]?.title || '';
    return [labelFromTitle(seedTitle, stopwords), c.items.length];
  });

  const dist = {};
  for (const [k, v] of top) dist[k] = v;
  const covered = top.reduce((s, [, v]) => s + v, 0);
  if (rows.length > covered) dist['其他'] = rows.length - covered;

  const engagement = rows.map(r => ({ views: toNumber(r.views), replies: toNumber(r.replies) }));
  const avgReplies = engagement.length ? engagement.reduce((s, x) => s + x.replies, 0) / engagement.length : 0;
  const avgViews = engagement.length ? engagement.reduce((s, x) => s + x.views, 0) / engagement.length : 0;
  const timelyCount = rows.filter(r => /(今天|明天|本周|今晚|周末|截止|预约|报名)/.test(r.title || '')).length;

  return {
    topCategories: top,
    dist,
    avgReplies,
    avgViews,
    timelyCount,
    matchedRate: rows.length ? covered / rows.length : 0,
  };
}

function buildConclusions(rows, result) {
  const lines = [];
  const top3 = Object.entries(result.dist).sort((a, b) => b[1] - a[1]).slice(0, 3);
  if (top3.length) lines.push(`1. 当前讨论集中在：${top3.map(([k, v]) => `${k}(${v})`).join('、')}。`);
  lines.push(`2. 平均互动强度：回复 ${result.avgReplies.toFixed(1)} / 浏览 ${result.avgViews.toFixed(1)}。`);
  lines.push(`3. 自动聚类覆盖率约 ${(result.matchedRate * 100).toFixed(0)}%，可在 topic-config.json 持续补充停用词优化。`);
  if (result.timelyCount > 0) {
    lines.push(`4. 时效性话题占比 ${Math.round((result.timelyCount / Math.max(rows.length, 1)) * 100)}%，建议优先在高活跃时段发。`);
  }
  return lines;
}

function buildReport(rows, result) {
  const topCats = Object.entries(result.dist).sort((a, b) => b[1] - a[1]);
  const lines = [];
  lines.push('# Xinsheng 社区趋势简报');
  lines.push('');
  lines.push(`- 样本数：${rows.length}`);
  lines.push(`- 自动主题：${topCats.slice(0, 5).map(([k, v]) => `${k}(${v})`).join('、') || '无'}`);
  lines.push(`- 聚类标签：${result.topCategories.map(([k, v]) => `${k}(${v})`).join('、') || '无'}`);
  lines.push('');
  lines.push('## 趋势结论');
  lines.push(...buildConclusions(rows, result));
  lines.push('');
  lines.push('## 运营建议');
  lines.push('- 直接用自动主题 Top5 做下周选题池。');
  lines.push('- 每周复盘“其他”类标题并更新 references/topic-config.json。');
  lines.push('- 跟踪连续两周的主题迁移，决定是否做固定栏目。');
  return lines.join('\n');
}

function main(argv = process.argv) {
  const args = parseArgs(argv);
  if (!args.input) {
    console.error('Usage: node analyze_trends.js --input <posts.json> [--out report.md] [--top 8] [--config topic-config.json]');
    process.exit(1);
  }
  const rows = JSON.parse(fs.readFileSync(args.input, 'utf8'));
  const cfg = loadConfig(args.config);
  const result = analyzeRows(rows, args.top, cfg);
  const report = buildReport(rows, result);

  if (args.out) {
    fs.writeFileSync(args.out, report, 'utf8');
    console.log(`Saved report to ${args.out}`);
  } else {
    console.log(report);
  }
}

if (require.main === module) main();

module.exports = { parseArgs, loadConfig, tokenizeTitle, analyzeRows, buildReport, main };
