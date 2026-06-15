// B站解析：BV 号 → view 取信息 → playurl(html5) 取免登录 mp4(durl)
// 注意：B站视频 CDN 有 Referer 防盗链，预览/保存通常需开启 PROXY_TO_STORAGE 转存
//（已通过 result.downloadHeaders 把 Referer 透传给云函数转存）。
const { httpGet, resolveRedirect } = require('../lib/http');
const { videoResult } = require('../lib/result');

const platform = 'bilibili';
const HDR = { Referer: 'https://www.bilibili.com/', Origin: 'https://www.bilibili.com' };

function match(u) {
  return /bilibili\.com|b23\.tv|acg\.tv/.test(u);
}

async function getJson(url) {
  const res = await httpGet(url, { headers: HDR });
  return JSON.parse(res.body);
}

async function parse(url) {
  const real = await resolveRedirect(url);
  const bv = (real.match(/BV[0-9A-Za-z]+/) || url.match(/BV[0-9A-Za-z]+/) || [])[0];
  if (!bv) throw new Error('bilibili: no BV id');

  const view = await getJson(`https://api.bilibili.com/x/web-interface/view?bvid=${bv}`);
  const d = view && view.data;
  if (!d || !d.cid) throw new Error('bilibili: view failed');

  const playurl = `https://api.bilibili.com/x/player/playurl?bvid=${bv}&cid=${d.cid}&qn=16&platform=html5&fnval=1&otype=json`;
  const pu = await getJson(playurl);
  const durl = pu && pu.data && pu.data.durl && pu.data.durl[0] && pu.data.durl[0].url;
  if (!durl) throw new Error('bilibili: no playable url');

  const r = videoResult({
    platform,
    id: bv,
    title: d.title || 'B站视频',
    url: durl,
    cover: d.pic || '',
    author: (d.owner && d.owner.name) || '',
  });
  r.downloadHeaders = HDR; // 转存时带上 Referer 绕过防盗链
  return r;
}

module.exports = { platform, match, parse };
