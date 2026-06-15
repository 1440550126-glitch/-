// 抖音解析：短链跳转 → 分享 H5 页 → 提取 window._ROUTER_DATA 中的无水印地址
// 说明：抖音前端结构会不定期调整，这里做了多路径兜底；生产建议配合第三方接口兜底。
const { httpGet, resolveRedirect, UA_MOBILE } = require('../lib/http');
const { videoResult, imageResult } = require('../lib/result');

const platform = 'douyin';

function match(u) {
  return /douyin\.com|iesdouyin\.com/.test(u);
}

function shareHeaders() {
  return { 'User-Agent': UA_MOBILE, Referer: 'https://www.douyin.com/', Accept: 'text/html,*/*' };
}

// 字符串感知的 JSON 截取：从 from 位置的 '{' 开始，找到配对的 '}'
function sliceJson(s, from) {
  let depth = 0;
  let inStr = false;
  let esc = false;
  for (let i = from; i < s.length; i += 1) {
    const c = s[i];
    if (inStr) {
      if (esc) esc = false;
      else if (c === '\\') esc = true;
      else if (c === '"') inStr = false;
      continue;
    }
    if (c === '"') inStr = true;
    else if (c === '{') depth += 1;
    else if (c === '}') {
      depth -= 1;
      if (depth === 0) return s.slice(from, i + 1);
    }
  }
  return '';
}

function extractRouterData(html) {
  const key = 'window._ROUTER_DATA';
  const i = html.indexOf(key);
  if (i < 0) return null;
  const start = html.indexOf('{', i);
  if (start < 0) return null;
  const json = sliceJson(html, start);
  if (!json) return null;
  try {
    return JSON.parse(json);
  } catch (e) {
    return null;
  }
}

// 从 loaderData 里挑出包含作品详情的那一项
function pickDetail(data) {
  if (!data || !data.loaderData) return null;
  for (const k of Object.keys(data.loaderData)) {
    const v = data.loaderData[k];
    if (!v) continue;
    if (v.videoInfoRes && Array.isArray(v.videoInfoRes.item_list) && v.videoInfoRes.item_list[0]) {
      return v.videoInfoRes.item_list[0];
    }
    if (v.aweme_detail) return v.aweme_detail;
    if (Array.isArray(v.item_list) && v.item_list[0]) return v.item_list[0];
  }
  return null;
}

function bestUrl(list) {
  if (!Array.isArray(list) || !list.length) return '';
  const cleaned = list.map((x) => String(x).replace(/\\u002F/g, '/'));
  const httpsFirst = cleaned.filter((x) => /^https/.test(x));
  return httpsFirst[0] || cleaned[0] || '';
}

function noWatermark(u) {
  return u
    .replace('/playwm/', '/play/')
    .replace('playwm', 'play')
    .replace(/watermark=1/g, 'watermark=0');
}

function coverOf(d) {
  const v = d.video || {};
  const c = v.cover || v.origin_cover || v.dynamic_cover;
  return c ? bestUrl(c.url_list || []) : '';
}

function normalize(d, id) {
  if (!d) return null;
  const title =
    (d.desc || (d.share_info && d.share_info.share_title) || (d.preview_title) || '抖音作品').trim();
  const author = (d.author && d.author.nickname) || '';

  // 图集
  const images = d.images || d.image_list;
  if (Array.isArray(images) && images.length) {
    const urls = images
      .map((im) => bestUrl(im.url_list || (im.display_image && im.display_image.url_list) || []))
      .filter(Boolean);
    if (urls.length) return imageResult({ platform, id, title, author, images: urls, cover: coverOf(d) });
  }

  // 视频
  const v = d.video || {};
  let urls = (v.play_addr && v.play_addr.url_list) || [];
  if ((!urls || !urls.length) && Array.isArray(v.bit_rate) && v.bit_rate[0] && v.bit_rate[0].play_addr) {
    urls = v.bit_rate[0].play_addr.url_list || [];
  }
  const play = bestUrl(urls);
  if (!play) return null;
  return videoResult({ platform, id, title, author, url: noWatermark(play), cover: coverOf(d) });
}

// 解析失败时，从 HTML 里直接搜 mp4 直链兜底
function regexFallback(html, id) {
  const m = html.match(/https?:\\?\/\\?\/[^"'\s]*?\.mp4[^"'\s]*/);
  if (!m) return null;
  const url = noWatermark(m[0].replace(/\\u002F/g, '/').replace(/\\\//g, '/'));
  return videoResult({ platform, id, title: '抖音作品', url });
}

async function parse(url) {
  const real = await resolveRedirect(url);
  const idMatch =
    real.match(/(?:video|note)\/(\d+)/) ||
    real.match(/[?&](?:modal_id|item_ids|aweme_id)=(\d+)/);
  const id = idMatch ? idMatch[idMatch.length - 1] : '';

  const res = await httpGet(real, { headers: shareHeaders() });
  const data = extractRouterData(res.body);
  const detail = pickDetail(data);

  const r = normalize(detail, id) || regexFallback(res.body, id);
  if (!r) throw new Error('douyin parse failed');
  return r;
}

module.exports = { platform, match, parse };
// 导出内部函数供离线单测使用
module.exports._t = { sliceJson, extractRouterData, pickDetail, normalize, noWatermark, bestUrl };
