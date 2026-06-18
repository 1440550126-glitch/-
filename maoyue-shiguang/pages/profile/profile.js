// pages/profile/profile.js — 我的：关系 / 主题 / 会员 / 实名 / 设置
const store = require('../../utils/store.js');
const seccheck = require('../../utils/seccheck.js');
const app = getApp();

const AVATARS = ['🐱', '🐰', '🐻', '🦊', '🐼', '🐶']; // showActionSheet 最多 6 项
const THEMES = [
  { key: 'coral', name: '珊瑚粉' }, { key: 'latte', name: '奶咖' },
  { key: 'morandi', name: '莫兰迪' }, { key: 'macaron', name: '马卡龙' }, { key: 'night', name: '暗夜' }
];

Page({
  data: {
    theme: 'coral',
    themeName: '珊瑚粉',
    couple: {},
    loveDays: 1,
    statCount: 0,
    isMember: false,
    memberTier: '',
    verified: false,
    showBindCine: false   // 鹊桥相会过场
  },

  onShow() { this.refresh(); },

  refresh() {
    const theme = store.getTheme();
    const tObj = THEMES.filter(t => t.key === theme)[0] || THEMES[0];
    const m = store.getMember();
    const link = store.getLink();
    this.setData({
      theme: theme,
      themeName: tObj.name,
      couple: store.getCouple(),
      loveDays: store.loveDays(),
      statCount: store.getStat().count || 0,
      isMember: m.isMember,
      memberTier: m.tier,
      verified: store.isVerified(),
      // 已生成邀请码但 TA 还没加入 → 显示"等待加入"提示
      waitingInvite: !!(link.coupleId && !store.getCouple().bound),
      inviteCode: link.inviteCode || ''
    });
  },

  // ── 主题 ──
  pickTheme() {
    wx.showActionSheet({
      itemList: THEMES.map(t => t.name),
      success: (res) => { store.setTheme(THEMES[res.tapIndex].key); this.refresh(); wx.showToast({ title: '主题已切换', icon: 'none' }); }
    });
  },

  editName(e) {
    const who = e.currentTarget.dataset.who;
    const key = who === 'self' ? 'selfName' : 'partnerName';
    wx.showModal({
      title: who === 'self' ? '我的昵称' : 'TA的昵称', editable: true,
      placeholderText: this.data.couple[key], confirmColor: '#F2658A',
      success: async (res) => {
        if (!res.confirm || !res.content) return;
        const name = res.content.trim();
        if (!(await seccheck.checkText(name))) return;   // 内容安全校验
        const p = {}; p[key] = name; store.setCouple(p); app.refreshCouple(); this.refresh();
      }
    });
  },

  pickAvatar(e) {
    const who = e.currentTarget.dataset.who;
    const key = who === 'self' ? 'selfAvatar' : 'partnerAvatar';
    wx.showActionSheet({
      itemList: AVATARS,
      success: (res) => { const p = {}; p[key] = AVATARS[res.tapIndex]; store.setCouple(p); app.refreshCouple(); this.refresh(); }
    });
  },

  onStartDate(e) { store.setCouple({ startDate: e.detail.value }); app.refreshCouple(); this.refresh(); },

  toggleBind() {
    if (this.data.couple.bound) return this.doUnbind();
    if (!store.cloudReady()) return this.localBind();   // 未开通云开发 → 本地绑定（原型可用）
    const link = store.getLink();
    const items = link.coupleId ? ['查看我的邀请码', '输入TA的邀请码'] : ['生成我的邀请码（发给TA）', '输入TA的邀请码'];
    wx.showActionSheet({ itemList: items, success: (r) => { if (r.tapIndex === 0) this.genInvite(); else this.joinByCode(); } });
  },

  // 生成自己的邀请码，发给 TA（TA 用「输入邀请码」加入后即双向同步）
  genInvite() {
    wx.showLoading({ title: '生成中…' });
    store.bindCouple('', (res) => {
      wx.hideLoading();
      if (!res || !res.ok) return wx.showToast({ title: '生成失败，请重试', icon: 'none' });
      app.refreshCouple(); this.refresh();
      const code = res.inviteCode || store.getLink().inviteCode;
      wx.showModal({
        title: '我的邀请码', content: '把这串码发给 TA，TA 在「绑定关系 → 输入TA的邀请码」里填入，就能和你同步啦：\n\n' + code,
        confirmText: '复制邀请码', cancelText: '关闭', confirmColor: '#F2658A',
        success: (m) => { if (m.confirm) wx.setClipboardData({ data: code, success: () => wx.showToast({ title: '已复制，发给 TA 吧', icon: 'none' }) }); }
      });
    });
  },

  // 输入 TA 的邀请码加入关系
  joinByCode() {
    wx.showModal({
      title: '输入 TA 的邀请码', editable: true, placeholderText: '例如 ABC234', confirmColor: '#F2658A',
      success: (r) => {
        if (!r.confirm) return;
        const code = (r.content || '').trim().toUpperCase();
        if (!code) return wx.showToast({ title: '请输入邀请码', icon: 'none' });
        wx.showLoading({ title: '绑定中…' });
        store.bindCouple(code, (res) => {
          wx.hideLoading();
          if (!res || !res.ok) {
            const map = { CODE_NOT_FOUND: '邀请码不存在', COUPLE_FULL: 'TA 已经和别人绑定啦' };
            return wx.showToast({ title: (res && map[res.error]) || '绑定失败，请重试', icon: 'none' });
          }
          app.refreshCouple();
          this.playBindCine();   // 鹊桥相会过场
        });
      }
    });
  },

  // 未开通云开发时的本地绑定（与原型一致：只翻转本地标记）
  localBind() { store.bindCouple('', () => { app.refreshCouple(); this.playBindCine(); }); },

  doUnbind() {
    if (!store.isMember()) {
      wx.showModal({
        title: '🔓 解绑需会员', content: '解除情侣绑定是会员功能。开通会员后可随时解绑。',
        confirmText: '去开通', confirmColor: '#F2658A',
        success: (res) => { if (res.confirm) this.goMembership(); }
      });
      return;
    }
    wx.showModal({
      title: '解除绑定？', content: '解除后将停止与 TA 的同步、不再显示"在一起"的天数；本地的回忆和纪念日会保留。',
      confirmColor: '#F2658A',
      success: (res) => { if (res.confirm) store.unbindCouple(() => { app.refreshCouple(); this.refresh(); wx.showToast({ title: '已解除绑定', icon: 'none' }); }); }
    });
  },

  playBindCine() {
    this.setData({ showBindCine: true });   // 鹊桥相会过场 + 古风音效
    this.playCineAudio();
    clearTimeout(this._cine);
    this._cine = setTimeout(() => { this.setData({ showBindCine: false }); this.stopCineAudio(); this.refresh(); wx.showToast({ title: '我们在鹊桥相遇 💞', icon: 'none' }); }, 6800);
  },

  playCineAudio() {
    try { const a = wx.createInnerAudioContext(); a.src = '/assets/audio/cine.mp3'; a.volume = 0.9; a.play(); a.onError(() => { try { a.destroy(); } catch (e) {} }); this._cineAudio = a; } catch (e) {}
  },
  stopCineAudio() { if (this._cineAudio) { try { this._cineAudio.stop(); this._cineAudio.destroy(); } catch (e) {} this._cineAudio = null; } },

  skipCine() { clearTimeout(this._cine); this.setData({ showBindCine: false }); this.stopCineAudio(); this.refresh(); },

  onHide() { clearTimeout(this._cine); this.setData({ showBindCine: false }); this.stopCineAudio(); },
  onUnload() { clearTimeout(this._cine); this.stopCineAudio(); },

  goMembership() { wx.navigateTo({ url: '/pages/membership/membership' }); },
  goVerify() { wx.navigateTo({ url: '/pages/verify/verify' }); },

  inviteTa() {
    wx.setClipboardData({ data: '来「猫约时光」和我一起记录每一天吧～', success: () => wx.showToast({ title: '邀请语已复制，发给TA吧', icon: 'none' }) });
  },

  clearData() {
    wx.showModal({
      title: '清空所有数据？', content: '心情、纸条、纪念日、回忆、猫咪、金库记录都会被清空，且无法恢复。',
      confirmText: '清空', confirmColor: '#F2658A',
      success: (res) => { if (res.confirm) { try { wx.clearStorageSync(); } catch (e) {} store.ensureDefaults(); app.refreshCouple(); this.refresh(); wx.showToast({ title: '已清空', icon: 'success' }); } }
    });
  },

  goLegal(e) {
    const doc = (e.currentTarget.dataset.doc) || 'privacy';
    wx.navigateTo({ url: '/pages/legal/legal?doc=' + doc });
  },

  about() {
    wx.showModal({
      title: '关于 猫约时光',
      content: '一个情侣陪伴小程序：记录在一起的日子、心情纸条、共同小金库、一起养猫，把你们的每一天好好收藏。',
      showCancel: false, confirmText: '好的', confirmColor: '#F2658A'
    });
  }
});
