// cloudfunctions/pay/index.js — 微信支付（会员开通）云函数
//
// actions:
//   unifiedOrder : 入参 planKey（monthly/yearly/forever）→ 按金额统一下单，
//                  返回客户端 wx.requestPayment 所需的支付参数。
//   query        : 查询调用者（按 OPENID）的会员状态。
//
// 另导出 payCallback：作为「支付结果回调」函数，由微信支付在用户付款成功后调用，
// 校验通过后把该 openid 的会员状态写入 users 集合。
//
// 数据：集合 users = { _id: openid, member:{ isMember, tier, since, orderNo }, updatedAt }
// 会员是「按用户(个人)」的，不是情侣共享，故单独存 users（不复用 couples）。
//
// ┌──────────────────────────────────────────────────────────────────────┐
// │ ⚠️ 上线前【必须由开发者配置】以下项，否则 unifiedOrder 走「未配置」降级： │
// │  1. 开通【微信支付商户号】（mp.weixin.qq.com → 微信支付），完成签约。       │
// │  2. 云开发后台「设置 → 其他设置」绑定该商户号（让云函数可代调统一下单）。     │
// │  3. 填好下方 PAY_CONFIG 占位常量：SUB_MCH_ID（子商户号）、ENV_ID（当前环境 │
// │     ID，用于回调拼装）、CALLBACK_FUNCTION（本回调函数名，默认 pay_payCallback）。│
// │  4. 部署本云函数（右键「上传并部署：云端安装依赖」），并新建 users 集合。     │
// └──────────────────────────────────────────────────────────────────────┘
const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();
const users = db.collection('users');

// ───────── 需开发者填写的支付配置（占位，集中放此处）─────────
const PAY_CONFIG = {
  SUB_MCH_ID: '',                       // 子商户号（在云开发后台绑定商户号后填入）
  ENV_ID: '',                           // 云开发环境 ID（回调地址需要，留空用当前环境）
  CALLBACK_FUNCTION: 'pay_payCallback', // 支付回调函数名：本云函数名_payCallback
  BODY_PREFIX: '猫约时光会员-'          // 下单商品描述前缀
};

// 套餐 → 金额（分）/ 会员档位名。outTradeNo 唯一。
const PLANS = {
  monthly: { fee: 1800, label: '月卡' },
  yearly: { fee: 13800, label: '年卡' },
  forever: { fee: 29800, label: '永久会员' }
};

// 商户是否已配置（缺必要常量则视为未配置 → 优雅降级，不抛异常）
function payConfigured() {
  return !!PAY_CONFIG.SUB_MCH_ID;
}

// 生成唯一订单号：MY + 时间戳 + 随机串（仅大写字母与数字）
function outTradeNo() {
  const rand = Math.random().toString(36).slice(2, 10).toUpperCase();
  return 'MY' + Date.now() + rand;
}

// 把会员状态写入 users 集合（存在则更新，不存在则创建）。回调与查询复用。
async function grantMember(openid, tier, orderNo) {
  const member = {
    isMember: true,
    tier: tier || 'monthly',
    since: new Date().toISOString().slice(0, 10), // YYYY-MM-DD
    orderNo: orderNo || ''
  };
  try {
    await users.doc(openid).update({ data: { member, updatedAt: Date.now() } });
  } catch (e) {
    // 文档不存在：新建（_id 用 openid，保证一人一条）
    await users.doc(openid).set({ data: { _id: openid, member, updatedAt: Date.now() } });
  }
  return member;
}

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { ok: false, error: 'NO_OPENID' };
  const action = event && event.action;

  try {
    if (action === 'unifiedOrder') {
      // 未配置商户：优雅降级，让客户端转「模拟开通」（不抛异常）
      if (!payConfigured()) return { ok: false, error: 'PAY_NOT_CONFIGURED' };

      const planKey = event.planKey;
      const plan = PLANS[planKey];
      if (!plan) return { ok: false, error: 'UNKNOWN_PLAN' };

      const tradeNo = outTradeNo();
      // 云开发统一下单：成功返回的 payment 即 wx.requestPayment 所需参数
      const res = await cloud.cloudPay.unifiedOrder({
        body: PAY_CONFIG.BODY_PREFIX + plan.label,
        outTradeNo: tradeNo,
        spbillCreateIp: '127.0.0.1',
        subMchId: PAY_CONFIG.SUB_MCH_ID,
        totalFee: plan.fee,                      // 单位：分
        envId: PAY_CONFIG.ENV_ID || cloud.DYNAMIC_CURRENT_ENV,
        functionName: PAY_CONFIG.CALLBACK_FUNCTION // 支付成功后微信回调的函数
      });
      return { ok: true, payment: res && res.payment, orderNo: tradeNo, tier: planKey };
    }

    if (action === 'query') {
      const r = await users.doc(OPENID).get().catch(() => null);
      const member = (r && r.data && r.data.member) || { isMember: false, tier: '', since: '', orderNo: '' };
      return { ok: true, member };
    }

    return { ok: false, error: 'UNKNOWN_ACTION' };
  } catch (e) {
    return { ok: false, error: (e && (e.errMsg || e.message)) || String(e) };
  }
};

// 支付结果回调：微信支付付款成功后自动调用本函数（函数名见 PAY_CONFIG.CALLBACK_FUNCTION）。
// event 内含 outTradeNo / resultCode / openid 等支付结果字段。校验通过才发放会员。
exports.payCallback = async (event) => {
  try {
    // resultCode === 'SUCCESS' 表示用户付款成功
    if (!event || event.resultCode !== 'SUCCESS') {
      return { errcode: 1, errmsg: 'PAYMENT_NOT_SUCCESS' };
    }
    const openid = event.openid || (cloud.getWXContext() && cloud.getWXContext().OPENID);
    if (!openid) return { errcode: 1, errmsg: 'NO_OPENID' };

    // 从订单描述里还原档位（前缀 + label）；取不到则按月卡兜底
    const body = event.body || '';
    let tier = 'monthly';
    if (body.indexOf('永久') >= 0) tier = 'forever';
    else if (body.indexOf('年卡') >= 0) tier = 'yearly';

    await grantMember(openid, tier, event.outTradeNo || '');
    // 回调必须返回 { errcode: 0 } 告知微信已成功处理，否则会重试
    return { errcode: 0, errmsg: 'OK' };
  } catch (e) {
    return { errcode: 1, errmsg: (e && (e.errMsg || e.message)) || String(e) };
  }
};
