// 极简 HTTP 客户端：基于 Node 内置 https/http，零依赖，支持手动跟随 302 跳转
const https = require('https');
const http = require('http');
const { URL } = require('url');

const UA_MOBILE =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1';

function request(url, opts = {}) {
  const { method = 'GET', headers = {}, redirect = 'follow', maxRedirects = 6 } = opts;
  return new Promise((resolve, reject) => {
    let u;
    try {
      u = new URL(url);
    } catch (e) {
      return reject(new Error('invalid url'));
    }
    const mod = u.protocol === 'http:' ? http : https;
    const req = mod.request(
      u,
      { method, headers: { 'User-Agent': UA_MOBILE, Accept: '*/*', ...headers } },
      (res) => {
        const status = res.statusCode || 0;
        const loc = res.headers.location;

        if (loc && status >= 300 && status < 400) {
          const next = new URL(loc, u).toString();
          res.resume(); // 丢弃跳转响应体
          if (redirect === 'manual') {
            return resolve({ status, headers: res.headers, body: '', finalUrl: url, location: next });
          }
          if (maxRedirects <= 0) return reject(new Error('too many redirects'));
          return resolve(request(next, { method, headers, redirect, maxRedirects: maxRedirects - 1 }));
        }

        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const buffer = Buffer.concat(chunks);
          resolve({ status, headers: res.headers, body: buffer.toString('utf8'), buffer, finalUrl: url });
        });
      }
    );
    req.on('error', reject);
    req.setTimeout(12000, () => req.destroy(new Error('timeout')));
    req.end();
  });
}

function httpGet(url, opts = {}) {
  return request(url, { ...opts, method: 'GET' });
}

// 一直跟随跳转，返回最终落地的真实地址（不下载正文）
async function resolveRedirect(url) {
  let cur = url;
  for (let i = 0; i < 6; i += 1) {
    const r = await request(cur, { method: 'GET', redirect: 'manual' });
    if (r.location) {
      cur = r.location;
      continue;
    }
    return r.finalUrl || cur;
  }
  return cur;
}

async function downloadBuffer(url, headers = {}) {
  const r = await request(url, { method: 'GET', headers });
  return r.buffer;
}

module.exports = { request, httpGet, resolveRedirect, downloadBuffer, UA_MOBILE };
