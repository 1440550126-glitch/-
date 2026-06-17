// pages/membership/membership.js — 会员中心（已配置微信支付则真实开通，否则模拟开通）
const store = require('../../utils/store.js');
const pay = require('../../utils/pay.js');

const PLANS = [
  { key: 'monthly', name: '月卡', price: '18', per: '/月', tag: '' },
  { key: 'yearly', name: '年卡', price: '138', per: '/年', tag: '超值' },
  { key: 'forever', name: '永久会员', price: '298', per: '一次性', tag: '推荐' }
];
const PERKS = [
  { e: '☁️', t: '云端同步与备份，换手机数据不丢' },
  { e: '💔', t: '可随时解绑情侣关系' },
  { e: '🎨', t: '全部主题皮肤任意切换' },
  { e: '📸', t: '回忆相册扩容，珍藏更多瞬间' },
  { e: '✨', t: '专属会员标识与纪念日提醒' }
];

Page({
  data: { theme: 'coral', isMember: false, tier: '', plans: PLANS, perks: PERKS },

  onShow() { this.refresh(); },
  refresh() {
    const m = store.getMember();
    this.setData({ theme: store.getTheme(), isMember: m.isMember, tier: m.tier });
  },

  open(e) {
    const key = e.currentTarget.dataset.key;
    const plan = PLANS.filter(p => p.key === key)[0];
    // 已配置微信支付 → 真实下单付款；否则保持原型「模拟开通」交互
    if (pay.configured()) return this.buyReal(key, plan);
    this.openSimulated(key, plan);
  },

  // 真实支付：拉起微信收银台，付款成功后落地本地会员态
  async buyReal(key, plan) {
    wx.showLoading({ title: '正在下单…', mask: true });
    let r;
    try { r = await pay.buy(key); } catch (e) { r = { ok: false, reason: 'pay_failed' }; }
    wx.hideLoading();
    if (r && r.ok) {
      store.openMember(key);
      this.refresh();
      wx.showToast({ title: '已开通会员 👑', icon: 'success' });
      return;
    }
    // 商户暂未配置：回退到模拟开通，保证可体验
    if (r && r.reason === 'not_configured') return this.openSimulated(key, plan);
    if (r && r.reason === 'cancel') return; // 用户主动取消，静默
    const tip = { order_failed: '下单失败，请稍后再试', pay_failed: '支付未完成，请重试' };
    wx.showToast({ title: (r && tip[r.reason]) || '支付未完成', icon: 'none' });
  },

  // 模拟开通（原型/未配置支付）：弹窗确认后直接置会员态，不真实扣款
  openSimulated(key, plan) {
    wx.showModal({
      title: '确认开通', content: '开通「' + plan.name + '」 ¥' + plan.price + plan.per + '\n\n（原型阶段：点击确认即模拟开通，不会真实扣款）',
      confirmText: '开通', confirmColor: '#F2658A',
      success: (res) => {
        if (!res.confirm) return;
        store.openMember(key);
        this.refresh();
        wx.showToast({ title: '已开通会员 👑', icon: 'success' });
      }
    });
  },

  cancelMember() {
    wx.showModal({
      title: '仅供测试', content: '关闭会员状态（方便你测试门禁效果）？',
      success: (res) => { if (res.confirm) { store.cancelMember(); this.refresh(); wx.showToast({ title: '已关闭会员', icon: 'none' }); } }
    });
  }
});
