const app = getApp();
const { version } = require('../../utils/version');

Page({
  data: { email: '', version },

  onLoad() {
    this.setData({ email: app.globalData.config.contactEmail || '' });
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
