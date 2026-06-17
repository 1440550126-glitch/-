// pages/cat/cat.js — 猫窝：你们一起养的猫（免费 · 靠陪伴喂养）
const store = require('../../utils/store.js');

Page({
  data: {
    theme: 'coral',
    cat: {},
    expPct: 0,
    msg: '',
    levelBanner: false,
    levelText: '',
    floatHeart: false,
    floatEmoji: '🐾'
  },

  onShow() { this.refresh(); },

  refresh(extra) {
    const cat = store.getCat();
    this.setData(Object.assign({
      theme: store.getTheme(),
      cat: cat,
      expPct: Math.min(100, Math.floor((cat.exp / cat.expMax) * 100))
    }, extra || {}));
  },

  popHeart(emoji) {
    this.setData({ floatHeart: true, floatEmoji: emoji || '🐾' });
    setTimeout(() => this.setData({ floatHeart: false }), 1100);
  },

  handle(result, emoji) {
    if (result.limited) { wx.showToast({ title: result.msg, icon: 'none' }); this.refresh(); return; }
    this.popHeart(emoji);
    this.refresh({ msg: result.msg });
    if (result.leveledUp) {
      this.setData({ levelBanner: true, levelText: store.getCat().name + ' 升到了 Lv.' + result.cat.level + ' 🎉' });
      setTimeout(() => this.setData({ levelBanner: false }), 1800);
    }
  },

  feed() { this.handle(store.feedCat(), '🍚'); },
  pet() { this.handle(store.petCat(), '💗'); },
  play() { this.handle(store.playCat(), '🎀'); },

  rename() {
    wx.showModal({
      title: '给猫咪取名', editable: true, placeholderText: this.data.cat.name,
      confirmColor: '#F2658A',
      success: (res) => {
        if (res.confirm && res.content) { store.renameCat(res.content); this.refresh(); }
      }
    });
  }
});
