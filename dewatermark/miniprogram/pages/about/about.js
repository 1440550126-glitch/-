const app = getApp();
const { version } = require('../../utils/version');
const quota = require('../../utils/quota');
const { buildShare, grantShare } = require('../../utils/share');

Page({
  data: { email: '', version, freeBalance: 0, shareReward: 0, shareLeft: 0, showCredits: false },

  onLoad() {
    this.setData({
      email: app.globalData.config.contactEmail || '',
      showCredits: !!app.globalData.config.requireAdToDownload,
    });
  },

  onShow() {
    this.loadQuota();
  },

  loadQuota() {
    if (!app.globalData.config.requireAdToDownload) return;
    quota.get().then((q) => {
      if (!q) return;
      this.setData({
        freeBalance: (q.credits || 0) + (q.daily ? q.daily.left : 0),
        shareReward: q.share ? q.share.reward : 0,
        shareLeft: q.share ? q.share.left : 0,
      });
    });
  },

  onShareAppMessage() {
    grantShare();
    // 稍后刷新余额展示
    setTimeout(() => this.loadQuota(), 1500);
    return buildShare();
  },

  openDoc(e) {
    wx.navigateTo({ url: `/pages/doc/doc?type=${e.currentTarget.dataset.type}` });
  },

  goHistory() {
    wx.switchTab({ url: '/pages/history/history' });
  },

  copyEmail() {
    if (!this.data.email) return;
    wx.setClipboardData({ data: this.data.email, success: () => wx.showToast({ title: '邮箱已复制', icon: 'none' }) });
  },

  // 连点版本号 5 次进入数据看板（权限由 stats 云函数按 openid 校验）
  tapVersion() {
    this._taps = (this._taps || 0) + 1;
    if (this._taps >= 5) {
      this._taps = 0;
      wx.navigateTo({ url: '/pages/admin/admin' });
    }
  },
});
