// utils/api.js — 后端地址 / Token / 请求封装 / 登录 / 实时地址
// 留空 API_BASE 则保持纯本地原型（不连后端）；填上即接后端 maoyue-server。
const API_BASE = '';                 // 例：'https://你的域名/api'
const WS_BASE = '';                  // 例：'wss://你的域名/ws'（开发者工具本机调试可用 ws://localhost:3001/ws）

function getToken() { return wx.getStorageSync('token') || ''; }
function setToken(t) { wx.setStorageSync('token', t); }

function request(path, { method = 'GET', data } = {}) {
  return new Promise((resolve, reject) => {
    if (!API_BASE) return reject(new Error('API_BASE 未配置（纯本地模式）'));
    wx.request({
      url: API_BASE + path, method, data,
      header: { 'Content-Type': 'application/json', ...(getToken() ? { Authorization: 'Bearer ' + getToken() } : {}) },
      success: r => (r.data && r.data.code === 0) ? resolve(r.data.data) : reject(r.data || r),
      fail: reject
    });
  });
}

// 微信登录：wx.login -> 后端 /auth/login（jsCode 换 openid）
async function login() {
  const { code } = await wx.login();
  const data = await request('/auth/login', { method: 'POST', data: { jsCode: code } });
  setToken(data.token);
  return data.user;
}

// 实时连接地址（带 token）。未配置或未登录则返回空串。
function wsUrl() { return (WS_BASE && getToken()) ? (WS_BASE + '?token=' + getToken()) : ''; }

module.exports = { API_BASE, WS_BASE, getToken, setToken, request, login, wsUrl };
