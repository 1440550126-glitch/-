const DOCS = require('./docs');

Page({
  data: { title: '', updated: '', paras: [] },

  onLoad(q) {
    const d = DOCS[q.type] || DOCS.agreement;
    wx.setNavigationBarTitle({ title: d.title });
    this.setData({ title: d.title, updated: d.updated, paras: d.paras });
  },
});
