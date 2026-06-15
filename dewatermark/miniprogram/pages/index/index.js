const app = getApp();
const { detect } = require('../../utils/link');
const { callParse } = require('../../utils/cloud');

Page({
  data: {
    input: '',
    detected: null, // { name, supported }
    parsing: false,
    bannerUnitId: '',
    platforms: ['抖音', '快手', '小红书'],
  },

  onLoad() {
    this.setData({ bannerUnitId: app.globalData.config.bannerAdUnitId || '' });
  },

  onInput(e) {
    const v = e.detail.value;
    this.setData({ input: v, detected: v.trim() ? detect(v) : null });
  },

  async paste() {
    try {
      const r = await wx.getClipboardData();
      const v = r.data || '';
      if (!v) {
        wx.showToast({ title: '剪贴板是空的', icon: 'none' });
        return;
      }
      this.setData({ input: v, detected: detect(v) });
    } catch (e) {
      wx.showToast({ title: '读取剪贴板失败', icon: 'none' });
    }
  },

  clearInput() {
    this.setData({ input: '', detected: null });
  },

  async onParse() {
    const text = this.data.input.trim();
    if (!text) {
      wx.showToast({ title: '请先粘贴分享链接', icon: 'none' });
      return;
    }
    const d = this.data.detected || detect(text);
    if (!d.url) {
      wx.showToast({ title: '没找到有效链接', icon: 'none' });
      return;
    }
    this.setData({ parsing: true });
    wx.showLoading({ title: '解析中…', mask: true });
    try {
      const data = await callParse(text);
      app.globalData.lastResult = data;
      wx.hideLoading();
      wx.navigateTo({ url: '/pages/result/result' });
    } catch (err) {
      wx.hideLoading();
      wx.showModal({
        title: '解析失败',
        content: (err && err.message) || '请确认链接有效后重试',
        showCancel: false,
      });
    } finally {
      this.setData({ parsing: false });
    }
  },

  goHistory() {
    wx.switchTab({ url: '/pages/history/history' });
  },
});
