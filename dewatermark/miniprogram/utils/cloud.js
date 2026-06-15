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

module.exports = { callParse };
