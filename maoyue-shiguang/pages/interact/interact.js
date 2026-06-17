// pages/interact/interact.js — 陪伴：情侣日常互动
const store = require('../../utils/store.js');
const seccheck = require('../../utils/seccheck.js');

const MOODS = [
  { e: '😊', t: '开心' }, { e: '🥰', t: '想你' }, { e: '😌', t: '平静' },
  { e: '😴', t: '累了' }, { e: '🥲', t: '想被哄' }, { e: '😋', t: '满足' }, { e: '😤', t: '有点气' }, { e: '🤒', t: '不舒服' }
];
const POKE_REPLIES = [
  'TA回头看了你一眼 👀', 'TA也戳了戳你 👈', 'TA："干嘛呀～" 😆', 'TA被你戳得笑了 😄', 'TA："再戳要亲你了哦" 😚'
];

Page({
  data: {
    theme: 'coral',
    moods: MOODS,
    mood: {},
    pokeCount: 0,
    dailyQ: {},
    answerInput: '',
    notes: [],
    noteInput: '',
    todayCount: 0,
    floatHeart: false,
    floatEmoji: '💗'
  },

  onShow() { this.refresh(); this._sub(); },
  onHide() { this._unsub(); },
  onUnload() { this._unsub(); },

  // 实时：TA 贴来新纸条即时出现
  _sub() {
    const app = getApp(); this._unsub();
    this._subs = [app.onRealtime('note.created', d => {
      if (!d) return;
      const notes = this.data.notes.slice();
      notes.unshift({ id: d.id || Date.now(), text: d.text || '', mine: false, timeStr: '刚刚' });
      this.setData({ notes: notes });
      wx.showToast({ title: 'TA 给你贴了张纸条 💌', icon: 'none' });
    })];
  },
  _unsub() { if (this._subs) { this._subs.forEach(f => f && f()); this._subs = null; } },

  refresh() {
    this.setData({
      theme: store.getTheme(),
      mood: store.getMood(),
      dailyQ: store.getDailyQuestion(),
      notes: this.decorate(store.getNotes()),
      todayCount: store.getStat().count || 0
    });
  },

  decorate(list) {
    return list.map(n => {
      const d = new Date(n.time);
      n.timeStr = (d.getMonth() + 1) + '/' + d.getDate() + ' ' + (d.getHours() < 10 ? '0' : '') + d.getHours() + ':' + (d.getMinutes() < 10 ? '0' : '') + d.getMinutes();
      n.mine = n.from === 'self';
      return n;
    });
  },

  popHeart(emoji) {
    this.setData({ floatHeart: true, floatEmoji: emoji || '💗' });
    setTimeout(() => this.setData({ floatHeart: false }), 1100);
  },

  // ── 戳一戳 ──
  poke() {
    store.logInteraction('poke');
    const n = this.data.pokeCount + 1;
    this.setData({ pokeCount: n });
    this.popHeart('👉');
    setTimeout(() => {
      wx.showToast({ title: POKE_REPLIES[Math.floor(Math.random() * POKE_REPLIES.length)], icon: 'none' });
    }, 500);
    this.setData({ todayCount: store.getStat().count || 0 });
  },

  // ── 今日心情 ──
  chooseMood(e) {
    const m = MOODS[e.currentTarget.dataset.i];
    store.setSelfMood(m.e, m.t);
    this.popHeart(m.e);
    this.refresh();
    wx.showToast({ title: '心情已和TA同步 ' + m.e, icon: 'none' });
  },

  // ── 每日一问 ──
  onAnswerInput(e) { this.setData({ answerInput: e.detail.value }); },
  submitAnswer() {
    const v = (this.data.answerInput || '').trim();
    if (!v) { wx.showToast({ title: '写点什么吧～', icon: 'none' }); return; }
    store.answerDailyQuestion(v);
    this.setData({ answerInput: '' });
    this.popHeart('💕');
    this.refresh();
  },

  // ── 爱的小纸条 ──
  onNoteInput(e) { this.setData({ noteInput: e.detail.value }); },
  async sendNote() {
    const v = (this.data.noteInput || '').trim();
    if (!v) { wx.showToast({ title: '写句话给TA吧', icon: 'none' }); return; }
    if (!(await seccheck.checkText(v))) return;   // 内容安全校验
    store.addNote(v);
    this.setData({ noteInput: '' });
    this.popHeart('💌');
    this.refresh();
  },
  delNote(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '删除这张纸条？', content: '撕掉就找不回来啦',
      confirmColor: '#F2658A',
      success: (res) => { if (res.confirm) { store.removeNote(id); this.refresh(); } }
    });
  }
});
