// app.js — 猫约时光（情侣陪伴版）
const store = require('./utils/store.js');
const api = require('./utils/api.js');
const realtime = require('./utils/realtime.js');

// 云开发环境 ID：在微信后台开通「云开发」后填入（留空则用默认环境）。
// 云数据库/云存储/云函数（含内容安全 secCheck）都依赖它。
const CLOUD_ENV = 'cloud1-d7gpe7xa5720e6963';

App({
  globalData: {
    couple: null,
    cloudReady: false,
    realtime
  },

  onLaunch() {
    // 初始化云开发（用于数据同步与内容安全 secCheck 云函数）
    if (wx.cloud) {
      try {
        wx.cloud.init(CLOUD_ENV ? { env: CLOUD_ENV, traceUser: true } : { traceUser: true });
        this.globalData.cloudReady = true;
      } catch (e) { this.globalData.cloudReady = false; }
    }
    store.ensureDefaults();
    this.globalData.couple = store.getCouple();
    this.connectRealtime();
    store.beginSync(() => this.afterSync());   // 首次拉取云端共享数据 → 刷新当前页
  },

  onShow() {
    store.recordOpen();
    this.reportMyPresence();                                  // 上报我的在线/电量
    if (this._booted) store.syncNow(() => this.afterSync());  // 回到前台：拉取 TA 的最新改动
    this._booted = true;
    store.startRealtime((p) => this.afterSync(p));            // 开启准实时（watch / 轮询）
  },
  onHide() { store.recordHide(); store.stopRealtime(); store.syncNow(); },  // 退后台：停实时 + 推送本地改动

  // 上报本机电量与在线时间（位置由「TA 的状态」页在开启共享时上报）
  reportMyPresence() {
    let battery, charging;
    try { const b = wx.getBatteryInfoSync(); battery = b.level; charging = !!b.isCharging; } catch (e) {}
    store.reportPresence({ battery: battery, charging: charging });
  },

  // 云同步落地后刷新当前页面（页面普遍有 refresh()，无需逐页改造）；并提示对方的戳一戳
  afterSync(payload) {
    this.refreshCouple();
    const ps = getCurrentPages();
    const top = ps && ps[ps.length - 1];
    if (top && typeof top.refresh === 'function') { try { top.refresh(); } catch (e) {} }
    if (payload && payload.poke) {
      const map = { poke: 'TA 戳了戳你 👉', miss: 'TA 想你了 💭', hug: 'TA 抱了抱你 🤗', kiss: 'TA 亲了你一下 😚' };
      wx.showToast({ title: map[payload.poke.type] || 'TA 戳了戳你 👉', icon: 'none' });
    }
  },

  // 建立 WebSocket 实时连接（未配置后端/未登录则自动跳过，纯本地原型照常用）
  connectRealtime() {
    const url = api.wsUrl();
    if (!url) return;
    realtime.init(url);
    // 全局：收到 TA 的传情/戳一戳 → 顶部轻提示（任意页面都能收到）
    realtime.on('affection.received', d => {
      const map = { miss: 'TA 想你了 💭', hug: 'TA 抱了抱你 🤗', kiss: 'TA 亲了你一下 😚', poke: 'TA 戳了戳你 👉', night: 'TA 对你说晚安 🌙' };
      wx.showToast({ title: (d && map[d.type]) || 'TA 给你发来一条互动 💗', icon: 'none' });
    });
  },

  // 页面订阅实时事件的便捷入口，返回取消订阅函数
  onRealtime(event, cb) { return realtime.on(event, cb); },

  refreshCouple() {
    this.globalData.couple = store.getCouple();
    return this.globalData.couple;
  }
});
