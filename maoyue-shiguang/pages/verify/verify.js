// pages/verify/verify.js — 实名认证（原型：模拟；正式上线需后端对接权威核验）
const store = require('../../utils/store.js');

Page({
  data: { theme: 'coral', verified: false, name: '', nameInput: '', idInput: '' },

  onShow() { this.refresh(); },
  refresh() {
    const v = store.getVerify();
    this.setData({ theme: store.getTheme(), verified: v.status === 'verified', name: v.name });
  },

  onName(e) { this.setData({ nameInput: e.detail.value }); },
  onId(e) { this.setData({ idInput: e.detail.value }); },

  submit() {
    const name = (this.data.nameInput || '').trim();
    const id = (this.data.idInput || '').trim();
    if (!name) { wx.showToast({ title: '请输入真实姓名', icon: 'none' }); return; }
    if (id.length < 15) { wx.showToast({ title: '请输入有效证件号', icon: 'none' }); return; }
    wx.showLoading({ title: '核验中…' });
    setTimeout(() => {
      wx.hideLoading();
      store.setVerified(name);
      this.refresh();
      wx.showToast({ title: '实名认证成功 ✓', icon: 'success' });
    }, 1000);
  }
});
