const config = require('./config');
const quota = require('./utils/quota');

App({
  globalData: {
    config,
    openid: '',
    // 当天已用免费下载次数（跨页共享，按自然日重置）
    freeUsed: 0,
    freeDay: '',
    // 邀请人 openid（来自分享链接 ?ref=），登录后用于归因
    pendingRef: '',
    refBound: false,
  },

  onLaunch(options) {
    if (!wx.cloud) {
      console.error('当前基础库过低，请使用 2.2.3 及以上');
      return;
    }
    wx.cloud.init({ env: config.cloudEnv, traceUser: true });
    this.resetDailyIfNeeded();
    this.captureRef(options);
    this.login();
  },

  // 从分享链接再次进入时也尝试捕获/归因
  onShow(options) {
    this.captureRef(options);
    this.tryBindReferrer();
  },

  captureRef(options) {
    const ref = options && options.query && options.query.ref;
    if (ref && !this.globalData.refBound) this.globalData.pendingRef = ref;
  },

  login() {
    wx.cloud
      .callFunction({ name: 'login' })
      .then((res) => {
        this.globalData.openid = (res.result && res.result.openid) || '';
        this.tryBindReferrer();
      })
      .catch(() => {});
  },

  // 完成登录且有待归因的邀请人时，绑定一次
  tryBindReferrer() {
    const { openid, pendingRef, refBound } = this.globalData;
    if (!openid || !pendingRef || refBound) return;
    this.globalData.refBound = true; // 防重复
    quota.bind(pendingRef).then((r) => {
      if (r && r.bound && r.newbieBonus) {
        wx.showToast({ title: `邀请奖励 +${r.newbieBonus} 次免广告`, icon: 'none' });
      }
    });
  },

  // 按自然日重置免费下载计数
  resetDailyIfNeeded() {
    const today = new Date().toISOString().slice(0, 10);
    if (this.globalData.freeDay !== today) {
      this.globalData.freeDay = today;
      this.globalData.freeUsed = 0;
    }
  },
});
