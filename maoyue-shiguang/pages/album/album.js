// pages/album/album.js — 手工剪纸 3D 相册：蝴蝶栖息/扇翅/乱飞/四散/回归 + 翻页 + 体感视差
const store = require('../../utils/store.js');
const rnd = (a, b) => Math.random() * (b - a) + a;
const HUES = [320, 40, 150, 235, 90];   // 给 🦋 染不同色相（粉/橙/绿/紫/黄绿）

function makeButterflies(n) {
  const arr = [];
  for (let i = 0; i < n; i++) {
    const ang = rnd(0, Math.PI * 2), dist = rnd(440, 780);
    arr.push({
      id: i, x: rnd(12, 80), y: rnd(12, 70), rot: rnd(-18, 18),
      hue: HUES[i % HUES.length],         // 颜色多样
      dur: rnd(0.4, 0.62).toFixed(2),     // 扇翅膀快慢（每只不同）
      scale: rnd(0.8, 1.25).toFixed(2),   // 每只大小不同
      // 四散飞走时的位移（朝随机方向飞出 + 缩小）
      fly: 'translate(' + (Math.cos(ang) * dist).toFixed(0) + 'rpx,' + (Math.sin(ang) * dist - 220).toFixed(0) + 'rpx) rotate(' + rnd(-70, 70).toFixed(0) + 'deg) scale(.3)'
    });
  }
  return arr;
}

Page({
  data: {
    theme: 'coral', memories: [], idx: 0, cur: null,
    opened: false, scattered: false, flipping: false, flipDir: 'next', butterflies: [],
    pBg: '', pMid: '', pFront: ''
  },

  onLoad() {
    this.setData({ theme: store.getTheme(), memories: store.getMemories(), butterflies: makeButterflies(5) });
    this.syncCur();
    this.startWander();      // 蝴蝶随机换位置（栖息状态下）
    this.startSensors();     // 体感视差（3D 立体）
  },
  onShow() { this.setData({ theme: store.getTheme(), memories: store.getMemories() }); this.syncCur(); },
  onHide() { this.stopAll(); },
  onUnload() { this.stopAll(); },

  syncCur() {
    const m = this.data.memories;
    this.setData({ idx: Math.min(this.data.idx, Math.max(0, m.length - 1)), cur: m.length ? m[Math.min(this.data.idx, m.length - 1)] : null });
  },

  // 翻开相册 → 蝴蝶四散
  open() {
    if (!this.data.memories.length) { wx.showToast({ title: '先去时光轴添加回忆吧', icon: 'none' }); return; }
    this.setData({ opened: true });
    this.scatter();
  },

  scatter() { this.setData({ scattered: true }); this.resetIdle(); },

  // 长时间不翻页 → 蝴蝶飞回来落在当前页
  resetIdle() {
    clearTimeout(this._idle);
    this._idle = setTimeout(() => {
      const b = this.data.butterflies.map(x => ({ ...x, x: rnd(12, 80), y: rnd(12, 70), rot: rnd(-22, 22) }));
      this.setData({ butterflies: b, scattered: false });
    }, 6000);
  },

  turn(dir) {
    const ni = this.data.idx + dir;
    if (ni < 0 || ni > this.data.memories.length - 1) return;
    this.setData({ idx: ni, flipping: true, flipDir: dir > 0 ? 'next' : 'prev' });
    this.syncCur();
    this.scatter();                                   // 翻页 → 蝴蝶四散
    clearTimeout(this._flip);
    this._flip = setTimeout(() => this.setData({ flipping: false }), 600);  // 翻书动画时长
  },
  next() { this.turn(1); },
  prev() { this.turn(-1); },

  startWander() {
    clearInterval(this._wander);
    this._wander = setInterval(() => {
      if (this.data.scattered) return;                 // 飞走时不乱动
      const b = this.data.butterflies.slice();
      const i = Math.floor(rnd(0, b.length));
      b[i] = { ...b[i], x: rnd(12, 80), y: rnd(12, 70), rot: rnd(-22, 22) };
      this.setData({ butterflies: b });
    }, 3600);   // 放慢：换位置更从容
  },

  startSensors() {
    try {
      wx.startAccelerometer({ interval: 'normal' });
      this._acc = (e) => {
        const tx = Math.max(-1, Math.min(1, e.x)), ty = Math.max(-1, Math.min(1, e.y));
        const mk = (m) => 'translate(' + (tx * m).toFixed(1) + 'rpx,' + (-ty * m).toFixed(1) + 'rpx)';
        this.setData({ pBg: mk(10), pMid: mk(24), pFront: mk(42) });   // 不同层不同位移 = 立体
      };
      wx.onAccelerometerChange(this._acc);
    } catch (e) {}
  },

  stopAll() {
    clearInterval(this._wander); clearTimeout(this._idle); clearTimeout(this._flip);
    try { if (this._acc) wx.offAccelerometerChange(this._acc); wx.stopAccelerometer(); } catch (e) {}
  },

  goTimeline() { wx.switchTab({ url: '/pages/timeline/timeline' }); }
});
