// pages/dining/dining.js — 情侣点餐：今天吃什么 + 自定义菜单
const store = require('../../utils/store.js');

Page({
  data: {
    theme: 'coral',
    menu: [],
    current: null,
    result: null,
    spinning: false,
    newDish: ''
  },

  onShow() { this.refresh(); },
  refresh() { this.setData({ theme: store.getTheme(), menu: store.getMenu() }); },

  spin() {
    if (this.data.spinning) return;
    const menu = this.data.menu;
    if (menu.length < 2) { wx.showToast({ title: '先多加几道菜吧', icon: 'none' }); return; }
    this.setData({ spinning: true, result: null });
    let n = 0;
    const total = 18 + Math.floor(Math.random() * 6);
    const tick = () => {
      this.setData({ current: menu[Math.floor(Math.random() * menu.length)] });
      n++;
      if (n >= total) {
        const r = menu[Math.floor(Math.random() * menu.length)];
        this.setData({ result: r, current: r, spinning: false });
        store.logInteraction('dining');
      } else {
        setTimeout(tick, 60 + n * 9);
      }
    };
    tick();
  },

  onNewDish(e) { this.setData({ newDish: e.detail.value }); },
  addDish() {
    const v = (this.data.newDish || '').trim();
    if (!v) { wx.showToast({ title: '写个菜名吧', icon: 'none' }); return; }
    store.addDish(v, '🍽️');
    this.setData({ newDish: '' });
    this.refresh();
  },
  removeDish(e) {
    store.removeDish(e.currentTarget.dataset.id);
    this.refresh();
  },

  sendToPartner() {
    if (!this.data.result) { wx.showToast({ title: '先转一个出来', icon: 'none' }); return; }
    store.logInteraction('dining');
    wx.showToast({ title: '已把「' + this.data.result.name + '」发给TA 🍜', icon: 'none' });
  }
});
