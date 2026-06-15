// 分享内容 + 分享得免广告次数
const quota = require('./quota');

function buildShare() {
  return {
    title: '这个去水印神器太好用了，无水印保存视频/图片！',
    path: '/pages/index/index',
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
