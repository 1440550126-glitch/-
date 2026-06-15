const config = require('./config');

App({
  globalData: {
    config,
    openid: '',
    // 当天已用免费下载次数（跨页共享，按自然日重置）
    freeUsed: 0,
    freeDay: '',
  },

  onLaunch() {
    if (!wx.cloud) {
      console.error('当前基础库过低，请使用 2.2.3 及以上');
      return;
    }
    wx.cloud.init({ env: config.cloudEnv, traceUser: true });
    this.resetDailyIfNeeded();
    this.login();
  },

  login() {
    wx.cloud
      .callFunction({ name: 'login' })
      .then((res) => {
        this.globalData.openid = (res.result && res.result.openid) || '';
      })
      .catch(() => {});
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
