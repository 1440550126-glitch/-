// pages/home/home.js — 家：情侣的温柔小屋
const store = require('../../utils/store.js');

const SEASON_TIP = function () {
  const m = new Date().getMonth() + 1;
  if (m >= 3 && m <= 5) return { e: '🌸', t: '春日正好，宜牵手散步' };
  if (m >= 6 && m <= 8) return { e: '🌊', t: '夏天到了，记得一起吃冰' };
  if (m >= 9 && m <= 11) return { e: '🍂', t: '秋意渐浓，适合依偎' };
  return { e: '❄️', t: '天冷了，要互相暖手哦' };
};

const AFFECTIONS = {
  miss: { emoji: '💭', toast: '已把"想你"送给TA 💭' },
  hug: { emoji: '🤗', toast: '一个大大的抱抱送出 🤗' },
  kiss: { emoji: '😚', toast: '么么哒已送达 😚' },
  night: { emoji: '🌙', toast: '晚安，今晚好梦 🌙' }
};
const SIM_REPLY = ['TA也想你了 💗', 'TA回了你一个抱抱 🤗', 'TA秒回："在呢～"', 'TA说："我也是 🥰"'];
function rnd(a, b) { return Math.floor(Math.random() * (b - a + 1)) + a; }

Page({
  data: {
    theme: 'coral',
    greet: '', dateStr: '', season: {},
    couple: {}, loveDays: 1, mood: {}, dailyQ: {}, partnerStat: {}, partnerCare: false,
    floatHeart: false, floatEmoji: '💗'
  },

  onShow() { this.refresh(); this._sub(); },
  onHide() { this._unsub(); },
  onUnload() { this._unsub(); },

  // 订阅实时事件（连了后端才会触发；纯本地时静默）
  _sub() {
    const app = getApp(); this._unsub();
    this._subs = [
      app.onRealtime('mood.updated', d => { if (d && d.mood) { this.setData({ 'mood.partner': d.mood }); wx.showToast({ title: 'TA 刚更新了心情 ' + d.mood.e, icon: 'none' }); } }),
      app.onRealtime('partner.status', d => { if (d) this.setData({ 'partnerStat.battery': d.battery != null ? d.battery : this.data.partnerStat.battery, 'partnerStat.online': !!d.online }); })
    ];
  },
  _unsub() { if (this._subs) { this._subs.forEach(f => f && f()); this._subs = null; } },

  refresh() {
    const now = new Date();
    const h = now.getHours();
    let greet = '你好呀';
    if (h < 6) greet = '夜深了，早点休息';
    else if (h < 11) greet = '早安，今天也要相爱';
    else if (h < 14) greet = '午安，记得好好吃饭';
    else if (h < 18) greet = '下午好，想TA了吗';
    else if (h < 23) greet = '晚上好，今天辛苦啦';
    else greet = '夜深了，早点睡哦';

    this.setData({
      theme: store.getTheme(),
      greet: greet,
      dateStr: (now.getMonth() + 1) + '月' + now.getDate() + '日 · 星期' + '日一二三四五六'[now.getDay()],
      season: SEASON_TIP(),
      couple: store.getCouple(),
      loveDays: store.loveDays(),
      mood: store.getMood(),
      dailyQ: store.getDailyQuestion(),
      partnerStat: store.getPartnerStatus(),
      partnerCare: store.partnerNeedsCare()
    });
  },

  sendAffection(e) {
    const a = AFFECTIONS[e.currentTarget.dataset.key];
    if (!a) return;
    store.logInteraction('affection');
    this.popHeart(a.emoji);
    wx.showToast({ title: a.toast, icon: 'none' });
    setTimeout(() => wx.showToast({ title: SIM_REPLY[Math.floor(Math.random() * SIM_REPLY.length)], icon: 'none' }), 1300);
  },

  popHeart(emoji) {
    this.setData({ floatHeart: true, floatEmoji: emoji || '💗' });
    setTimeout(() => this.setData({ floatHeart: false }), 1100);
  },

  pickMood() {
    const moods = [
      { e: '😊', t: '开心' }, { e: '🥰', t: '想你' }, { e: '😌', t: '平静' },
      { e: '😴', t: '累了' }, { e: '🥲', t: '想被哄' }, { e: '😋', t: '满足' }
    ];
    wx.showActionSheet({
      itemList: moods.map(m => m.e + '  ' + m.t),
      success: (res) => { const m = moods[res.tapIndex]; store.setSelfMood(m.e, m.t); this.popHeart(m.e); this.refresh(); }
    });
  },

  goInteract() { wx.switchTab({ url: '/pages/interact/interact' }); },
  goCat() { wx.navigateTo({ url: '/pages/cat/cat' }); },
  goTimeline() { wx.switchTab({ url: '/pages/timeline/timeline' }); },
  goDining() { wx.navigateTo({ url: '/pages/dining/dining' }); },
  goStatus() { wx.navigateTo({ url: '/pages/status/status' }); },
  goAlbum() { wx.navigateTo({ url: '/pages/album/album' }); },
  goMembership() { wx.navigateTo({ url: '/pages/membership/membership' }); },
  goBind() { wx.switchTab({ url: '/pages/profile/profile' }); },

  onShareAppMessage() { return { title: '猫约时光 · 和TA一起记录每一天', path: '/pages/home/home' }; }
});
