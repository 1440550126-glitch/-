// 云函数调用封装
function callParse(text) {
  return new Promise((resolve, reject) => {
    wx.cloud
      .callFunction({ name: 'parse', data: { text } })
      .then((res) => {
        const r = (res && res.result) || {};
        if (r.ok && r.data) resolve(r.data);
        else reject(new Error(r.msg || '解析失败，请稍后再试'));
      })
      .catch(() => reject(new Error('网络异常，请检查网络后重试')));
  });
}

// —— 解析记录云端同步（history 云函数）——
function historyAdd(record) {
  return wx.cloud
    .callFunction({ name: 'history', data: { action: 'add', record } })
    .then((r) => !!(r && r.result && r.result.ok))
    .catch(() => false);
}

function historyList(limit = 100) {
  return wx.cloud
    .callFunction({ name: 'history', data: { action: 'list', limit } })
    .then((r) => (r && r.result && r.result.list) || [])
    .catch(() => []);
}

function historyClear() {
  return wx.cloud
    .callFunction({ name: 'history', data: { action: 'clear' } })
    .then((r) => !!(r && r.result && r.result.ok))
    .catch(() => false);
}

module.exports = { callParse, historyAdd, historyList, historyClear };
