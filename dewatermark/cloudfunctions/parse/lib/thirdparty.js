// 可选：第三方去水印聚合接口兜底。内置解析失败时自动启用（需在云函数环境变量配置）。
//   THIRDPARTY_API  形如 https://api.example.com/parse?key=YOURKEY&url=
//                   （末尾带 url= 时直接拼接，否则自动追加 &url=）
// 不同服务返回结构不同，mapResult 里按你购买的服务做字段适配即可。
const { httpGet } = require('./http');
const { videoResult, imageResult } = require('./result');

function buildUrl(api, target) {
  const enc = encodeURIComponent(target);
  if (/url=$/.test(api)) return api + enc;
  return api + (api.includes('?') ? '&' : '?') + 'url=' + enc;
}

function mapResult(json) {
  const d = (json && (json.data || json.result || json)) || {};
  const title = d.title || d.desc || d.text || '';
  const cover = d.cover || d.cover_url || d.image || '';
  const platform = d.platform || d.source || 'unknown';

  const images = d.images || d.image_list || d.pics || d.imageList;
  if (Array.isArray(images) && images.length) {
    return imageResult({ platform, title, images, cover });
  }

  const video = d.url || d.video || d.video_url || d.play_url || d.nwm_video_url || d.downurl;
  if (video) return videoResult({ platform, title, url: video, cover });

  return null;
}

async function tryThirdParty(url) {
  const api = process.env.THIRDPARTY_API;
  if (!api) return null;
  const res = await httpGet(buildUrl(api, url), { headers: { Accept: 'application/json' } });
  let json;
  try {
    json = JSON.parse(res.body);
  } catch (e) {
    return null;
  }
  return mapResult(json);
}

module.exports = { tryThirdParty, mapResult };
