// 分享内容 + 分享得免广告次数
const quota = require('./quota');

// 分享链接带上自己的 openid 作为邀请人，新用户进入后用于归因
function buildShare() {
  let ref = '';
  if (typeof getApp === 'function') {
    const app = getApp();
    ref = (app && app.globalData && app.globalData.openid) || '';
  }
  return {
    title: '这个去水印神器太好用了，无水印保存视频/图片！',
    path: ref ? `/pages/index/index?ref=${ref}` : '/pages/index/index',
  };
}

// 分享触发时调用：发放奖励（服务端按每日上限封顶），并轻提示
function grantShare() {
  quota.reward('share').then((r) => {
    if (r && r.granted > 0) {
      wx.showToast({ title: `分享成功，+${r.granted} 次免广告`, icon: 'none' });
    }
  });
}

module.exports = { buildShare, grantShare };
