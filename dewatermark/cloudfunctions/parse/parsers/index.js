// 解析器注册与调度
const douyin = require('./douyin');
const kuaishou = require('./kuaishou');
const xiaohongshu = require('./xiaohongshu');

const REGISTRY = [douyin, kuaishou, xiaohongshu];

function findParser(url) {
  const u = String(url || '').toLowerCase();
  return REGISTRY.find((p) => p.match(u)) || null;
}

function detectPlatform(url) {
  const p = findParser(url);
  return p ? p.platform : 'unknown';
}

async function parse(url) {
  const p = findParser(url);
  if (!p) throw new Error('unsupported platform');
  return p.parse(url);
}

module.exports = { parse, detectPlatform, findParser, REGISTRY };
