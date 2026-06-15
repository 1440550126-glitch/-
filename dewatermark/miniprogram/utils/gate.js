// 下载前的「免广告额度 / 看广告」闸门，结果页与批量页共用
const quota = require('./quota');
const { showRewarded } = require('./ad');

// 返回 { allowed, free }：
//   allowed=false 表示用户没看完广告、放弃保存
//   free=true     表示走了免广告额度（保存失败时可退还）
async function passDownloadGate(cfg) {
  // 未开启广告门槛：直接放行
  if (!cfg.requireAdToDownload) return { allowed: true, free: true };

  // 优先用服务端免广告额度
  const s = await quota.spend();
  if (s) {
    if (s.spent) return { allowed: true, free: true, via: s.via };
    const ok = await showRewarded(cfg.rewardedAdUnitId);
    return { allowed: ok, free: false };
  }

  // 服务端不可用 → 回退到本地每日免费 + 广告
  const app = getApp();
  app.resetDailyIfNeeded();
  const freeLeft = (cfg.freeDownloadsPerDay || 0) - app.globalData.freeUsed;
  if (freeLeft > 0) {
    app.globalData.freeUsed += 1;
    return { allowed: true, free: true, via: 'local' };
  }
  const ok = await showRewarded(cfg.rewardedAdUnitId);
  return { allowed: ok, free: false };
}

// 免广告路径下保存失败，退还 1 次额度（best-effort）
function refund() {
  return quota.reward('refund');
}

module.exports = { passDownloadGate, refund };
