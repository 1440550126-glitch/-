const app = getApp();
const store = require('../../utils/store');

const NAMES = { douyin: '抖音', kuaishou: '快手', xiaohongshu: '小红书' };

function fmt(ts) {
  const d = new Date(ts);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getMonth() + 1}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

Page({
  data: { items: [] },

  onShow() {
    this.refresh();
  },

  refresh() {
    const items = store.list().map((it) => ({
      ...it,
      name: NAMES[it.platform] || '素材',
      time: fmt(it.at),
      count: it.type === 'image' ? (it.images || []).length : 1,
    }));
    this.setData({ items });
  },

  open(e) {
    const item = this.data.items[e.currentTarget.dataset.idx];
    if (!item) return;
    app.globalData.lastResult = item;
    wx.navigateTo({ url: '/pages/result/result' });
  },

  clearAll() {
    wx.showModal({
      title: '清空历史',
      content: '确定清空全部历史记录吗？记录仅保存在本机。',
      success: (r) => {
        if (r.confirm) {
          store.clear();
          this.refresh();
          wx.showToast({ title: '已清空', icon: 'none' });
        }
      },
    });
  },

  goIndex() {
    wx.switchTab({ url: '/pages/index/index' });
  },
});
