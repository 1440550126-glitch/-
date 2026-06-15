const app = getApp();
const { extractAll } = require('../../utils/link');
const { callParse, historyAdd } = require('../../utils/cloud');
const { showRewarded } = require('../../utils/ad');
const { saveMedia } = require('../../utils/save');
const { name } = require('../../utils/platform');
const store = require('../../utils/store');

const MAX = 20; // 单批上限
const CONCURRENCY = 2; // 并发解析数，避免对平台造成压力

Page({
  data: {
    input: '',
    items: [], // { url, status: pending|parsing|done|failed, name, title, cover, data, error }
    running: false,
    total: 0,
    doneCount: 0,
    savingAll: false,
  },

  onInput(e) {
    this.setData({ input: e.detail.value });
  },

  async paste() {
    try {
      const r = await wx.getClipboardData();
      this.setData({ input: r.data || '' });
    } catch (e) {}
  },

  start() {
    const urls = extractAll(this.data.input).slice(0, MAX);
    if (!urls.length) {
      wx.showToast({ title: '没识别到链接', icon: 'none' });
      return;
    }
    const items = urls.map((u) => ({ url: u, status: 'pending', name: '', title: '', cover: '', data: null, error: '' }));
    this.setData({ items, running: true, total: urls.length, doneCount: 0 });
    this.runQueue(urls);
  },

  async runQueue(urls) {
    let next = 0;
    let done = 0;
    const worker = async () => {
      while (next < urls.length) {
        const i = next;
        next += 1;
        this.patch(i, { status: 'parsing' });
        try {
          const data = await callParse(urls[i]);
          const rec = store.add(data);
          historyAdd(rec);
          this.patch(i, {
            status: 'done',
            data,
            name: name(data.platform),
            title: data.title || '',
            cover: data.cover || (data.images && data.images[0]) || '',
          });
        } catch (err) {
          this.patch(i, { status: 'failed', error: (err && err.message) || '解析失败' });
        }
        done += 1;
        this.setData({ doneCount: done });
      }
    };
    await Promise.all(Array.from({ length: Math.min(CONCURRENCY, urls.length) }, worker));
    this.setData({ running: false });
  },

  patch(i, obj) {
    const items = this.data.items.slice();
    items[i] = { ...items[i], ...obj };
    this.setData({ items });
  },

  async saveOne(e) {
    const it = this.data.items[e.currentTarget.dataset.idx];
    if (!it || !it.data) return;
    const cfg = app.globalData.config;
    if (cfg.requireAdToDownload) {
      const ok = await showRewarded(cfg.rewardedAdUnitId);
      if (!ok) {
        wx.showToast({ title: '看完广告才能保存', icon: 'none' });
        return;
      }
    }
    wx.showLoading({ title: '保存中…', mask: true });
    try {
      await saveMedia(it.data);
      wx.hideLoading();
      wx.showToast({ title: '已保存', icon: 'success' });
    } catch (err) {
      wx.hideLoading();
      wx.showModal({ title: '保存失败', content: (err && err.message) || '请重试', showCancel: false });
    }
  },

  // 看一次广告解锁「全部保存」
  async saveAll() {
    const dones = this.data.items.filter((x) => x.status === 'done' && x.data);
    if (!dones.length) {
      wx.showToast({ title: '没有可保存的内容', icon: 'none' });
      return;
    }
    const cfg = app.globalData.config;
    if (cfg.requireAdToDownload) {
      const ok = await showRewarded(cfg.rewardedAdUnitId);
      if (!ok) {
        wx.showToast({ title: '看完广告解锁全部保存', icon: 'none' });
        return;
      }
    }
    this.setData({ savingAll: true });
    let ok = 0;
    let fail = 0;
    for (const it of dones) {
      try {
        await saveMedia(it.data);
        ok += 1;
      } catch (e) {
        fail += 1;
      }
    }
    this.setData({ savingAll: false });
    wx.showModal({
      title: '保存完成',
      content: `成功 ${ok} 个${fail ? `，失败 ${fail} 个` : ''}`,
      showCancel: false,
    });
  },
});
