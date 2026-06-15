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
});
