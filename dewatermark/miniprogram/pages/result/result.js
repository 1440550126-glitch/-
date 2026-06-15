const app = getApp();
const { preloadRewarded } = require('../../utils/ad');
const { passDownloadGate, refund } = require('../../utils/gate');
const quota = require('../../utils/quota');
const { saveMedia } = require('../../utils/save');
const store = require('../../utils/store');
const { name } = require('../../utils/platform');
const { historyAdd } = require('../../utils/cloud');
const { buildShare, grantShare } = require('../../utils/share');

Page({
  data: {
    item: null,
    platformName: '',
    previewUrl: '',
    bannerUnitId: '',
    saving: false,
    freeBalance: 0,
    btnText: '看广告 · 保存到相册',
  },

  onLoad() {
    const item = app.globalData.lastResult;
    if (!item) {
      wx.showToast({ title: '数据已失效，请重新解析', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 900);
      return;
    }
    const cfg = app.globalData.config;
    const rec = store.add(item);
    historyAdd(rec); // 同步到云端（best-effort，不阻塞）

    this.setData({
      item,
      platformName: name(item.platform),
      // 已转存的视频优先用云存储临时地址预览（直链可能有防盗链，如 B站）
      previewUrl: item.fileID ? '' : item.url || '',
      bannerUnitId: cfg.bannerAdUnitId || '',
      btnText: cfg.requireAdToDownload ? '看广告 · 保存到相册' : '保存到相册',
    });

    preloadRewarded(cfg.rewardedAdUnitId);
    this.loadQuota();

    if (item.fileID) {
      wx.cloud
        .getTempFileURL({ fileList: [item.fileID] })
        .then((r) => {
          const f = r.fileList && r.fileList[0];
          if (f && f.tempFileURL) this.setData({ previewUrl: f.tempFileURL });
        })
        .catch(() => {});
    }
  },

  copyTitle() {
    const t = (this.data.item && this.data.item.title) || '';
    if (!t) return;
    wx.setClipboardData({ data: t, success: () => wx.showToast({ title: '文案已复制', icon: 'none' }) });
  },

  previewImage(e) {
    const url = e.currentTarget.dataset.url;
    wx.previewImage({ current: url, urls: this.data.item.images || [] });
  },

  loadQuota() {
    const cfg = app.globalData.config;
    if (!cfg.requireAdToDownload) {
      this.setData({ btnText: '保存到相册', freeBalance: 0 });
      return;
    }
    quota.get().then((q) => {
      if (!q) return; // 取不到则保持默认"看广告"文案
      const total = (q.credits || 0) + (q.daily ? q.daily.left : 0);
      this.setData({
        freeBalance: total,
        btnText: total > 0 ? `免广告保存（剩 ${total} 次）` : '看广告 · 保存到相册',
      });
    });
  },

  async onSave() {
    const cfg = app.globalData.config;
    const gate = await passDownloadGate(cfg);
    if (!gate.allowed) {
      wx.showToast({ title: '看完广告才能保存哦', icon: 'none' });
      this.loadQuota();
      return;
    }

    this.setData({ saving: true });
    wx.showLoading({ title: '保存中…', mask: true });
    try {
      await saveMedia(this.data.item);
      wx.hideLoading();
      wx.showToast({ title: '已保存到相册', icon: 'success' });
      this.maybeInterstitial();
    } catch (e) {
      wx.hideLoading();
      if (gate.free) refund(); // 免广告路径保存失败，退还额度
      wx.showModal({ title: '保存失败', content: (e && e.message) || '请重试', showCancel: false });
    } finally {
      this.setData({ saving: false });
      this.loadQuota();
    }
  },

  onShareAppMessage() {
    grantShare();
    return buildShare();
  },

  maybeInterstitial() {
    const id = app.globalData.config.interstitialAdUnitId;
    if (!id || !wx.createInterstitialAd) return;
    try {
      const ad = wx.createInterstitialAd({ adUnitId: id });
      ad.show().catch(() => {});
    } catch (e) {}
  },

  parseAnother() {
    wx.navigateBack();
  },
});
