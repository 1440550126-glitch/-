// 平台标识 → 展示名（前端多处复用）
const NAMES = {
  douyin: '抖音',
  kuaishou: '快手',
  xiaohongshu: '小红书',
  weibo: '微博',
  bilibili: 'B站',
  pipixia: '皮皮虾',
};

function name(p) {
  return NAMES[p] || '素材';
}

module.exports = { NAMES, name };
