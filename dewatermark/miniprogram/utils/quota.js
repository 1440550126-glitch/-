// 免广告额度（quota 云函数）封装。任何异常都返回 null，由调用方降级处理。
function call(data) {
  return wx.cloud
    .callFunction({ name: 'quota', data })
    .then((r) => (r && r.result && r.result.ok ? r.result : null))
    .catch(() => null);
}

function get() {
  return call({ action: 'get' });
}

function spend() {
  return call({ action: 'spend' });
}

function reward(reason) {
  return call({ action: 'reward', reason });
}

module.exports = { get, spend, reward };
