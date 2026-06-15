// 从粘贴的分享文案里提取链接并识别平台
const RULES = [
  { platform: 'douyin', name: '抖音', test: /douyin\.com|iesdouyin/i },
  { platform: 'kuaishou', name: '快手', test: /kuaishou|kwai|chenzhongtech|gifshow/i },
  { platform: 'xiaohongshu', name: '小红书', test: /xhslink|xiaohongshu/i },
  { platform: 'weibo', name: '微博', test: /weibo\.(com|cn)|video\.weibo|t\.cn|miaopai/i },
  { platform: 'bilibili', name: 'B站', test: /bilibili\.com|b23\.tv|acg\.tv/i },
  { platform: 'pipixia', name: '皮皮虾', test: /pipix\.com|pipixia/i },
];

function extractUrl(text) {
  const m = String(text || '').match(/https?:\/\/[^\s，。、）)】\]"']+/i);
  return m ? m[0].replace(/[)）】\]]+$/, '') : '';
}

function detect(text) {
  const url = extractUrl(text);
  const r = url ? RULES.find((x) => x.test.test(url)) : null;
  return {
    url,
    platform: r ? r.platform : 'unknown',
    name: r ? r.name : '未知平台',
    supported: !!r,
  };
}

module.exports = { extractUrl, detect, RULES };
