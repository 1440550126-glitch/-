// 激励视频广告封装（变现核心）
let rewardedAd = null;
let cachedUnitId = '';

function ensureRewarded(adUnitId) {
  if (!wx.createRewardedVideoAd || !adUnitId) return null;
  if (rewardedAd && cachedUnitId === adUnitId) return rewardedAd;
  cachedUnitId = adUnitId;
  rewardedAd = wx.createRewardedVideoAd({ adUnitId });
  rewardedAd.onError((err) => console.warn('[ad] rewarded error', err));
  return rewardedAd;
}

// 提前加载，进入结果页时调用，减少点击下载时的等待
function preloadRewarded(adUnitId) {
  const ad = ensureRewarded(adUnitId);
  if (ad) ad.load().catch(() => {});
}

// 展示激励视频。resolve(true)=看完，resolve(false)=中途关闭。
// 不支持广告组件的环境（如部分真机/开发者工具）直接放行 true，保证可用。
function showRewarded(adUnitId) {
  return new Promise((resolve) => {
    const ad = ensureRewarded(adUnitId);
    if (!ad) {
      resolve(true);
      return;
    }
    const onClose = (res) => {
      ad.offClose(onClose);
      // 低版本基础库 res 可能为 undefined，按看完处理
      const completed = !res || res.isEnded === undefined || res.isEnded === true;
      resolve(completed);
    };
    ad.onClose(onClose);
    ad.show().catch(() => {
      ad
        .load()
        .then(() => ad.show())
        .catch(() => {
          ad.offClose(onClose);
          resolve(true); // 广告加载失败时不卡住用户
        });
    });
  });
}

module.exports = { showRewarded, preloadRewarded };
