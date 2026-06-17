// pages/timeline/timeline.js — 时光：纪念日 / 回忆 / 共同愿望
const store = require('../../utils/store.js');
const seccheck = require('../../utils/seccheck.js');

Page({
  data: {
    theme: 'coral',
    annivs: [],
    memories: [],
    wishes: [],
    today: '',
    // 新增纪念日表单
    showAnnivForm: false,
    annivName: '',
    annivDate: '',
    annivRepeat: true,
    // 新增回忆表单
    showMemoForm: false,
    memoText: '',
    memoDate: '',
    memoPhoto: '',
    // 愿望
    wishInput: ''
  },

  onShow() { this.refresh(); },

  refresh() {
    this.setData({
      theme: store.getTheme(),
      annivs: store.getAnniversaries(),
      memories: store.getMemories(),
      wishes: store.getWishes(),
      today: store.todayStr()
    });
  },

  /* ── 纪念日 ── */
  toggleAnnivForm() {
    this.setData({ showAnnivForm: !this.data.showAnnivForm, annivName: '', annivDate: this.data.today, annivRepeat: true });
  },
  onAnnivName(e) { this.setData({ annivName: e.detail.value }); },
  onAnnivDate(e) { this.setData({ annivDate: e.detail.value }); },
  toggleRepeat() { this.setData({ annivRepeat: !this.data.annivRepeat }); },
  saveAnniv() {
    const name = (this.data.annivName || '').trim();
    if (!name) { wx.showToast({ title: '给这个日子起个名字', icon: 'none' }); return; }
    if (!this.data.annivDate) { wx.showToast({ title: '选个日期吧', icon: 'none' }); return; }
    store.addAnniversary(name, this.data.annivDate, this.data.annivRepeat);
    this.setData({ showAnnivForm: false });
    this.refresh();
    wx.showToast({ title: '已记下这个日子 💗', icon: 'none' });
  },
  delAnniv(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '删除这个纪念日？', confirmColor: '#F2658A',
      success: (res) => { if (res.confirm) { store.removeAnniversary(id); this.refresh(); } }
    });
  },

  /* ── 回忆 ── */
  toggleMemoForm() {
    this.setData({ showMemoForm: !this.data.showMemoForm, memoText: '', memoDate: this.data.today, memoPhoto: '' });
  },
  onMemoText(e) { this.setData({ memoText: e.detail.value }); },
  onMemoDate(e) { this.setData({ memoDate: e.detail.value }); },
  chooseMemoPhoto() {
    wx.chooseMedia({
      count: 1, mediaType: ['image'], sizeType: ['compressed'],
      success: (res) => { this.setData({ memoPhoto: res.tempFiles[0].tempFilePath }); }
    });
  },
  saveMemo() {
    const text = (this.data.memoText || '').trim();
    if (!text) { wx.showToast({ title: '写点什么吧', icon: 'none' }); return; }
    store.addMemory({ text: text, date: this.data.memoDate || this.data.today, photo: this.data.memoPhoto || '' });
    this.setData({ showMemoForm: false });
    this.refresh();
    wx.showToast({ title: '已收进时光轴 📖', icon: 'none' });
  },
  delMemo(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '删除这段回忆？', confirmColor: '#F2658A',
      success: (res) => { if (res.confirm) { store.removeMemory(id); this.refresh(); } }
    });
  },
  previewPhoto(e) {
    const src = e.currentTarget.dataset.src;
    if (src) wx.previewImage({ urls: [src] });
  },

  /* ── 愿望清单 ── */
  onWishInput(e) { this.setData({ wishInput: e.detail.value }); },
  async addWish() {
    const v = (this.data.wishInput || '').trim();
    if (!v) { wx.showToast({ title: '想一起做点什么呢？', icon: 'none' }); return; }
    if (!(await seccheck.checkText(v))) return;   // 内容安全校验
    store.addWish(v);
    this.setData({ wishInput: '' });
    this.refresh();
  },
  toggleWish(e) { store.toggleWish(e.currentTarget.dataset.id); this.refresh(); },
  delWish(e) {
    const id = e.currentTarget.dataset.id;
    store.removeWish(id); this.refresh();
  },

  goAlbum() { wx.navigateTo({ url: '/pages/album/album' }); }
});
