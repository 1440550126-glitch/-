// pages/vault/vault.js — 小金库：两人共同存钱/记账（投币/刷卡/开库 动画 + 音效）
const store = require('../../utils/store.js');

function fmt(n) {
  n = Math.round((n || 0) * 100) / 100;
  return (n % 1 === 0) ? ('' + n) : n.toFixed(2);
}
function playSound(src) {
  try {
    const a = wx.createInnerAudioContext();
    a.src = src; a.volume = 1; a.play();
    a.onEnded(() => a.destroy());
    a.onError(() => a.destroy());
  } catch (e) {}
}

Page({
  data: {
    theme: 'coral',
    bound: false,
    balanceStr: '0',
    stats: { totalIn: 0, totalOut: 0 },
    txns: [],
    mode: 'in',          // in 存钱 / out 记一笔花销
    amount: '',
    note: '',
    coins: [],           // 掉落金币
    showSwipe: false,    // 刷卡动画
    showVault: false,    // 开库金光动画
    vaultTier: 'empty',  // empty / coins / cash / gold（按余额）
    goldBars: 0,         // 金砖数量（1/2/3）
    crown: false         // 百万加皇冠
  },

  onShow() { this.refresh(); this._sub(); },
  onHide() { this._unsub(); },
  onUnload() { this._unsub(); },

  // 实时：对方存/取后，本端余额与流水即时更新
  _sub() {
    const app = getApp(); this._unsub();
    this._subs = [app.onRealtime('vault.updated', d => {
      if (!d) return;
      if (d.balance != null) this.setData({ balanceStr: (d.balance % 1 === 0) ? ('' + d.balance) : d.balance.toFixed(2) });
      this.refresh();
      wx.showToast({ title: 'TA 刚更新了金库 💰', icon: 'none' });
    })];
  },
  _unsub() { if (this._subs) { this._subs.forEach(f => f && f()); this._subs = null; } },

  refresh() {
    const v = store.getVault();
    this.setData({
      theme: store.getTheme(),
      bound: store.getCouple().bound,
      balanceStr: fmt(v.balance),
      stats: store.vaultStats(),
      txns: store.getVaultTx().slice(0, 30).map(t => {
        const d = new Date(t.time);
        t.timeStr = (d.getMonth() + 1) + '/' + d.getDate() + ' ' + (d.getHours() < 10 ? '0' : '') + d.getHours() + ':' + (d.getMinutes() < 10 ? '0' : '') + d.getMinutes();
        t.amountStr = fmt(t.amount);
        return t;
      })
    });
  },

  switchMode(e) { this.setData({ mode: e.currentTarget.dataset.m }); },
  onAmount(e) { this.setData({ amount: e.detail.value }); },
  onNote(e) { this.setData({ note: e.detail.value }); },

  submit() {
    const amount = parseFloat(this.data.amount);
    if (!amount || amount <= 0) { wx.showToast({ title: '输入一个金额吧', icon: 'none' }); return; }
    const note = (this.data.note || '').trim();
    if (this.data.mode === 'in') {
      store.vaultDeposit(amount, note || '存入小金库');
      this.setData({ amount: '', note: '' });
      this.refresh();
      this.coinRain();                                  // 投币动画
      playSound('/assets/audio/coin.wav');              // 投币音效
      wx.showToast({ title: '+ ¥' + fmt(amount) + ' 已存入 💰', icon: 'none' });
    } else {
      store.vaultSpend(amount, note || '一笔支出');
      this.setData({ amount: '', note: '' });
      this.refresh();
      this.swipe();                                     // 刷卡动画
      playSound('/assets/audio/swipe.wav');             // 刷卡音效
      wx.showToast({ title: '- ¥' + fmt(amount) + ' 已记账 💳', icon: 'none' });
    }
  },

  // 几十枚金币掉落进金库
  coinRain() {
    const coins = [];
    for (let i = 0; i < 26; i++) {
      coins.push({ id: i, left: Math.floor(Math.random() * 88) + 4, delay: (Math.random() * 0.5).toFixed(2), dur: (0.9 + Math.random() * 0.6).toFixed(2) });
    }
    this.setData({ coins: coins });
    setTimeout(() => this.setData({ coins: [] }), 1900);
  },

  // 刷卡
  swipe() {
    this.setData({ showSwipe: true });
    setTimeout(() => this.setData({ showSwipe: false }), 1100);
  },

  // 打开金库：按余额呈现不同场景（空库/硬币/纸钞/金砖×1~3+皇冠）
  openVault() {
    const bal = store.getVault().balance;
    let tier = 'empty', goldBars = 0, crown = false;
    if (bal >= 1000000) { tier = 'gold'; goldBars = 3; crown = true; }   // 百万：3 条 + 皇冠
    else if (bal >= 100000) { tier = 'gold'; goldBars = 2; }             // 十万：2 条
    else if (bal >= 10000) { tier = 'gold'; goldBars = 1; }              // 上万：1 条
    else if (bal >= 100) tier = 'cash';                                  // 几百：纸钞
    else if (bal >= 1) tier = 'coins';                                   // 几十：硬币
    this.setData({ showVault: true, vaultTier: tier, goldBars: goldBars, crown: crown });
    playSound(tier === 'empty' ? '/assets/audio/swipe.wav' : '/assets/audio/vault.wav'); // 空库放"风声"
  },
  closeVault() { this.setData({ showVault: false }); }
});
