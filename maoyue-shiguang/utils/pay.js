// utils/pay.js — 微信支付封装（会员开通）。独立于 coupleData，调用 pay 云函数。
//
// configured()      : 云开发已就绪 且 PAY_ENABLED 为 true（默认 false）。
//                     —— 没配好商户时保持 false，会员页自动走「模拟开通」。
// buy(planKey)      : 统一下单 → wx.requestPayment。返回 Promise，
//                     成功 resolve { ok:true }；失败/未配置 resolve { ok:false, reason }（不报错）。
// fetchMembership() : 查询当前用户云端会员态，resolve { isMember, tier, since, orderNo }，未就绪 resolve null。
//
// ⚠️ 上线前：开通微信支付商户号 + 云开发后台绑定商户号 + 部署 pay 云函数后，
//    把下面 PAY_ENABLED 改为 true（并在 cloudfunctions/pay/index.js 顶部填好 PAY_CONFIG）。
const PAY_ENABLED = false;

// 云开发是否就绪（与 utils/cloud.js 判定一致）
function cloudReady() {
  try {
    const app = getApp();
    return !!(wx.cloud && wx.cloud.callFunction && app && app.globalData && app.globalData.cloudReady);
  } catch (e) { return false; }
}

// 是否已具备真实支付条件
function configured() {
  return PAY_ENABLED && cloudReady();
}

// 调用 pay 云函数，返回 Promise<result>（未就绪 resolve null，调用失败 reject）
function callPay(action, data) {
  return new Promise((resolve, reject) => {
    if (!cloudReady()) return resolve(null);
    wx.cloud.callFunction({
      name: 'pay',
      data: Object.assign({ action: action }, data || {}),
      success: (r) => resolve(r && r.result),
      fail: (e) => reject(e)
    });
  });
}

// 发起购买：统一下单 → 拉起微信支付收银台。全程不抛异常，结果用 { ok, reason } 表达。
function buy(planKey) {
  return new Promise((resolve) => {
    if (!configured()) return resolve({ ok: false, reason: 'not_configured' });

    callPay('unifiedOrder', { planKey: planKey })
      .then((res) => {
        if (!res || !res.ok || !res.payment) {
          // 云函数侧未配置商户：PAY_NOT_CONFIGURED → 同样按未配置处理
          const reason = (res && res.error === 'PAY_NOT_CONFIGURED') ? 'not_configured' : ((res && res.error) || 'order_failed');
          return resolve({ ok: false, reason: reason });
        }
        // 用统一下单返回的参数拉起收银台
        wx.requestPayment(Object.assign({}, res.payment, {
          success: () => resolve({ ok: true, orderNo: res.orderNo, tier: res.tier }),
          fail: (e) => {
            const reason = (e && e.errMsg && e.errMsg.indexOf('cancel') >= 0) ? 'cancel' : 'pay_failed';
            resolve({ ok: false, reason: reason });
          }
        }));
      })
      .catch(() => resolve({ ok: false, reason: 'order_failed' }));
  });
}

// 查询云端会员态（可选）；未就绪或失败时 resolve null，由上层降级到本地。
function fetchMembership() {
  return new Promise((resolve) => {
    if (!cloudReady()) return resolve(null);
    callPay('query', {})
      .then((res) => resolve((res && res.ok && res.member) ? res.member : null))
      .catch(() => resolve(null));
  });
}

module.exports = { configured, buy, fetchMembership };
