// pages/status/status.js — TA 的状态：地图 / 电量 / 活跃 / 打开次数 / 使用时长 / 关心提醒
// 说明：自己的电量、打开次数、App内时长、定位为真实数据；TA 的状态原型为模拟，上线由后端实时同步。
//       系统级"其它App使用情况"小程序无法读取，故用"App内使用"代替。
const store = require('../../utils/store.js');

const REMIND_OPTS = [
  { label: '关闭提醒', enabled: false, minutes: 0 },
  { label: '超过 30 分钟', enabled: true, minutes: 30 },
  { label: '超过 1 小时', enabled: true, minutes: 60 },
  { label: '超过 2 小时', enabled: true, minutes: 120 },
  { label: '超过 4 小时', enabled: true, minutes: 240 }
];

Page({
  data: {
    theme: 'coral',
    couple: {},
    self: { battery: 100, charging: false },
    usage: {},
    partner: { battery: 0, activeStr: '', online: false },
    needsCare: false,
    remindLabel: '超过 2 小时',
    distance: '—',
    locShare: false,
    mapLat: 39.90819, mapLng: 116.39741, markers: [], hasLoc: false
  },

  onShow() {
    this.refresh();
    this.loadBattery();
    this.loadLocation();
  },

  refresh() {
    const ps = store.getPartnerStatus();
    const r = store.getRemind();
    const opt = REMIND_OPTS.filter(o => o.enabled === r.enabled && (!r.enabled || o.minutes === r.minutes))[0];
    this.setData({
      theme: store.getTheme(),
      couple: store.getCouple(),
      usage: store.getUsage(),
      partner: { battery: ps.battery, activeStr: ps.lastActiveStr, online: ps.online, waiting: !!ps.waiting, hasLoc: !!ps.hasLoc },
      needsCare: store.partnerNeedsCare(),
      remindLabel: opt ? opt.label : (r.enabled ? ('超过 ' + r.minutes + ' 分钟') : '关闭提醒'),
      locShare: !!r.locShare
    });
    if (this._selfLoc) this.renderMap(this._selfLoc.lat, this._selfLoc.lng);   // 用最新的对方位置刷新地图
  },

  loadBattery() {
    try { const b = wx.getBatteryInfoSync(); this.setData({ 'self.battery': b.level, 'self.charging': !!b.isCharging }); } catch (e) {}
  },

  loadLocation() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        const lat = res.latitude, lng = res.longitude;
        this._selfLoc = { lat: lat, lng: lng };
        // 开启共享时把我的位置上报，对方才能看到真实距离
        if (store.getRemind().locShare) store.reportPresence({ battery: this.data.self.battery, charging: this.data.self.charging, locOn: true, lat: lat, lng: lng });
        this.renderMap(lat, lng);
      },
      fail: () => { this.setData({ hasLoc: false }); }
    });
  },

  // 按"我的真实位置 + 对方上报的位置"渲染地图与距离
  renderMap(lat, lng) {
    const ps = store.getPartnerStatus();
    const c = this.data.couple;
    const markers = [{ id: 1, latitude: lat, longitude: lng, iconPath: '/assets/markers/self.png', width: 36, height: 42, anchor: { x: 0.5, y: 1 }, callout: { content: '我 ' + c.selfAvatar, display: 'ALWAYS', bgColor: '#FF7E9D', color: '#fff', fontSize: 12, borderRadius: 10, padding: 7 } }];
    let distance = '—';
    if (ps.real && ps.hasLoc) {
      markers.push({ id: 2, latitude: ps.lat, longitude: ps.lng, iconPath: '/assets/markers/partner.png', width: 36, height: 42, anchor: { x: 0.5, y: 1 }, callout: { content: 'TA ' + c.partnerAvatar, display: 'ALWAYS', bgColor: '#9E80D4', color: '#fff', fontSize: 12, borderRadius: 10, padding: 7 } });
      distance = this.distKm(lat, lng, ps.lat, ps.lng) + ' km';
    } else if (!ps.real) {
      // 未绑定：模拟一个距离，保留单人体验
      const plat = lat + (Math.random() - 0.5) * 0.05, plng = lng + (Math.random() - 0.5) * 0.05;
      distance = this.distKm(lat, lng, plat, plng) + ' km';
    }
    this.setData({ hasLoc: true, mapLat: lat, mapLng: lng, markers: markers, distance: distance });
  },

  // 位置共享开关（默认关闭，保护隐私）
  toggleLocShare() {
    const on = !store.getRemind().locShare;
    store.setRemind({ locShare: on });
    this.setData({ locShare: on });
    if (on && this._selfLoc) store.reportPresence({ battery: this.data.self.battery, charging: this.data.self.charging, locOn: true, lat: this._selfLoc.lat, lng: this._selfLoc.lng });
    else store.reportPresence({ battery: this.data.self.battery, charging: this.data.self.charging, locOn: false });
    wx.showToast({ title: on ? '已开启位置共享' : '已关闭位置共享', icon: 'none' });
    if (on) this.loadLocation();
  },

  distKm(la1, lo1, la2, lo2) {
    const R = 6371, rad = Math.PI / 180;
    const dLa = (la2 - la1) * rad, dLo = (lo2 - lo1) * rad;
    const a = Math.sin(dLa / 2) ** 2 + Math.cos(la1 * rad) * Math.cos(la2 * rad) * Math.sin(dLo / 2) ** 2;
    return (R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))).toFixed(1);
  },

  remindTa() {
    const r = store.pokePartner('poke');
    this.refresh();
    if (r.sim) wx.showToast({ title: r.responded ? 'TA 看到啦，上线回应了你 💗' : '已轻轻提醒，等TA上线 📳', icon: 'none' });
    else wx.showToast({ title: '已戳 TA 👉 ，TA 看到会知道你在想ta', icon: 'none' });
  },

  openRemindSetting() {
    wx.showActionSheet({
      itemList: REMIND_OPTS.map(o => o.label),
      success: (res) => {
        const o = REMIND_OPTS[res.tapIndex];
        store.setRemind({ enabled: o.enabled, minutes: o.minutes });
        this.refresh();
        wx.showToast({ title: o.enabled ? ('TA ' + o.label + '没看手机就提醒我') : '已关闭关心提醒', icon: 'none' });
      }
    });
  },

  reLocate() { this.loadLocation(); }
});
