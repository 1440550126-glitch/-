// utils/cloud.js — 云开发调用封装（未开通云开发时安全降级为 no-op）
//
// enabled()：是否已成功初始化云开发（app.onLaunch 里 wx.cloud.init 成功后置位）。
// call(action, data)：调用 coupleData 云函数，返回 Promise<result|null>。
//   未开通时 resolve(null)，调用失败 reject(err)，让上层自行降级。

function enabled() {
  try {
    const app = getApp();
    return !!(wx.cloud && app && app.globalData && app.globalData.cloudReady);
  } catch (e) { return false; }
}

function call(action, data) {
  return new Promise((resolve, reject) => {
    if (!enabled()) return resolve(null);
    wx.cloud.callFunction({
      name: 'coupleData',
      data: Object.assign({ action: action }, data || {}),
      success: (r) => resolve(r && r.result),
      fail: (e) => reject(e)
    });
  });
}

module.exports = { enabled, call };
