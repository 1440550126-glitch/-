const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();
const _ = db.command;

const COL = 'credits';

function int(v, d) {
  const n = parseInt(v, 10);
  return Number.isFinite(n) && n >= 0 ? n : d;
}

// 可用云函数环境变量覆盖（见 docs/DEPLOY.md）
const NEWBIE_FREE = int(process.env.NEWBIE_FREE, 3); // 新人初始免广告次数
const DAILY_FREE = int(process.env.DAILY_FREE, 0); // 每日额外免广告次数
const SHARE_REWARD = int(process.env.SHARE_REWARD, 2); // 每次分享奖励
const SHARE_DAILY_CAP = int(process.env.SHARE_DAILY_CAP, 3); // 每日可奖励分享次数

// —— 邀请裂变 ——
const REF_REWARD = int(process.env.REF_REWARD, 5); // 成功邀请 1 人，邀请人得
const REF_NEWBIE_BONUS = int(process.env.REF_NEWBIE_BONUS, 2); // 被邀请新人额外得
const REF_DAILY_CAP = int(process.env.REF_DAILY_CAP, 10); // 邀请人每日可获奖励的邀请数
const REF_BIND_WINDOW = int(process.env.REF_BIND_WINDOW_H, 24) * 3600000; // 仅此窗口内的新账号可被归因

function today() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

async function ensure(col, openid) {
  const r = await col.where({ openid }).limit(1).get();
  if (r.data && r.data[0]) return r.data[0];
  const doc = {
    openid,
    freeCredits: NEWBIE_FREE, // 新人赠送
    newbieGranted: true,
    dailyDay: today(),
    dailyUsed: 0,
    shareDay: today(),
    shareCount: 0,
    referredBy: '', // 被谁邀请（一次性）
    referredCount: 0, // 成功邀请了多少人
    refDay: today(),
    refCount: 0, // 当日已获奖励的邀请数
    created_at: Date.now(),
    updated_at: Date.now(),
  };
  const add = await col.add({ data: doc });
  doc._id = add._id;
  return doc;
}

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  const col = db.collection(COL);
  const action = event.action || 'get';

  try {
    const doc = await ensure(col, OPENID);
    const t = today();
    let dailyUsed = doc.dailyDay === t ? doc.dailyUsed || 0 : 0;
    let shareCount = doc.shareDay === t ? doc.shareCount || 0 : 0;

    // 扣减一次下载额度：优先每日免费，其次免广告额度；都没有则返回 spent=false（需看广告）
    if (action === 'spend') {
      let via = 'none';
      let spent = false;
      if (DAILY_FREE - dailyUsed > 0) {
        via = 'daily';
        spent = true;
        dailyUsed += 1;
      } else if ((doc.freeCredits || 0) > 0) {
        via = 'credit';
        spent = true;
      }
      const update = { dailyDay: t, dailyUsed, shareDay: t, shareCount, updated_at: Date.now() };
      if (via === 'credit') update.freeCredits = _.inc(-1);
      await col.doc(doc._id).update({ data: update });
      const credits = (doc.freeCredits || 0) - (via === 'credit' ? 1 : 0);
      return { ok: true, spent, via, credits, dailyLeft: Math.max(0, DAILY_FREE - dailyUsed) };
    }

    // 奖励额度：share=分享(每日封顶)，refund=保存失败退还(不封顶)
    if (action === 'reward') {
      const reason = event.reason || 'share';
      if (reason === 'refund') {
        await col.doc(doc._id).update({ data: { freeCredits: _.inc(1), updated_at: Date.now() } });
        return { ok: true, granted: 1, credits: (doc.freeCredits || 0) + 1 };
      }
      if (shareCount >= SHARE_DAILY_CAP) {
        return { ok: true, granted: 0, capped: true, credits: doc.freeCredits || 0, shareLeft: 0 };
      }
      shareCount += 1;
      await col.doc(doc._id).update({
        data: { freeCredits: _.inc(SHARE_REWARD), shareDay: t, shareCount, updated_at: Date.now() },
      });
      return {
        ok: true,
        granted: SHARE_REWARD,
        credits: (doc.freeCredits || 0) + SHARE_REWARD,
        shareLeft: Math.max(0, SHARE_DAILY_CAP - shareCount),
      };
    }

    // 邀请归因：被邀请的新人调用，给邀请人发奖励（严格防刷）
    if (action === 'bind') {
      const referrer = String(event.referrer || '').trim();
      if (!referrer || referrer === OPENID) return { ok: true, bound: false, reason: 'self_or_empty' };
      if (doc.referredBy) return { ok: true, bound: false, reason: 'already' };
      // 仅新账号可被归因（防老用户点链接刷量）
      if (Date.now() - (doc.created_at || 0) > REF_BIND_WINDOW) {
        return { ok: true, bound: false, reason: 'not_new' };
      }

      // 邀请人若还没有额度档案则补建，确保归因奖励不丢
      const rr = await col.where({ openid: referrer }).limit(1).get();
      const rdoc = (rr.data && rr.data[0]) || (await ensure(col, referrer));

      const t2 = today();
      const refCount = rdoc.refDay === t2 ? rdoc.refCount || 0 : 0;
      const rewardReferrer = refCount < REF_DAILY_CAP;

      // 绑定被邀请人 + 发新人额外奖励
      await col.doc(doc._id).update({
        data: { referredBy: referrer, freeCredits: _.inc(REF_NEWBIE_BONUS), updated_at: Date.now() },
      });
      // 奖励邀请人（每日封顶内）
      const rUpdate = { referredCount: _.inc(1), updated_at: Date.now() };
      if (rewardReferrer) {
        rUpdate.freeCredits = _.inc(REF_REWARD);
        rUpdate.refDay = t2;
        rUpdate.refCount = refCount + 1;
      }
      await col.doc(rdoc._id).update({ data: rUpdate });

      return { ok: true, bound: true, newbieBonus: REF_NEWBIE_BONUS, referrerRewarded: rewardReferrer };
    }

    // get：返回当前额度与策略（顺便持久化跨天重置）
    if (doc.dailyDay !== t || doc.shareDay !== t) {
      await col.doc(doc._id).update({ data: { dailyDay: t, dailyUsed, shareDay: t, shareCount, updated_at: Date.now() } });
    }
    return {
      ok: true,
      credits: doc.freeCredits || 0,
      daily: { used: dailyUsed, total: DAILY_FREE, left: Math.max(0, DAILY_FREE - dailyUsed) },
      share: { reward: SHARE_REWARD, cap: SHARE_DAILY_CAP, used: shareCount, left: Math.max(0, SHARE_DAILY_CAP - shareCount) },
      newbie: NEWBIE_FREE,
      invited: doc.referredCount || 0,
      referred: !!doc.referredBy,
      ref: { reward: REF_REWARD, bonus: REF_NEWBIE_BONUS },
    };
  } catch (e) {
    return { ok: false, msg: String((e && e.message) || e) };
  }
};
