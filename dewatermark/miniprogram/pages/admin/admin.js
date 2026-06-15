const { NAMES } = require('../../utils/platform');

const VIA_NAMES = { builtin: '内置解析', thirdparty: '第三方', unknown: '未知' };

Page({
  data: {
    loading: true,
    denied: false,
    hint: '',
    myOpenid: '',
    s: null,
    platformBars: [],
    viaList: [],
    updated: '',
  },

  onLoad() {
    this.load();
  },

  load() {
    this.setData({ loading: true });
    wx.cloud
      .callFunction({ name: 'stats' })
      .then((res) => {
        const r = (res && res.result) || {};
        if (!r.ok) {
          this.setData({
            loading: false,
            denied: true,
            myOpenid: r.openid || '',
            hint:
              r.code === 'NO_ADMIN'
                ? '尚未配置管理员。请把下面的 openid 加入 stats 云函数的 ADMIN_OPENIDS 环境变量后重试。'
                : '当前账号无权限查看数据看板。',
          });
          return;
        }
        const bp = (r.parse.byPlatform || []).filter((x) => x.n > 0);
        const max = Math.max(1, ...bp.map((x) => x.n));
        const platformBars = bp.map((x) => ({
          name: NAMES[x.key] || x.key,
          n: x.n,
          pct: Math.round((x.n / max) * 100),
        }));
        const viaList = (r.parse.byVia || []).map((x) => ({ name: VIA_NAMES[x.key] || x.key, n: x.n }));
        const d = new Date(r.generatedAt);
        const p = (n) => String(n).padStart(2, '0');
        this.setData({
          loading: false,
          denied: false,
          s: r,
          platformBars,
          viaList,
          updated: `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`,
        });
      })
      .catch(() => {
        this.setData({ loading: false, denied: true, hint: '加载失败，请确认 stats 云函数已部署。' });
      });
  },

  copyOpenid() {
    if (!this.data.myOpenid) return;
    wx.setClipboardData({ data: this.data.myOpenid, success: () => wx.showToast({ title: '已复制', icon: 'none' }) });
  },

  refresh() {
    this.load();
  },
});
