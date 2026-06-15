// 小红书解析：分享页 og 标签（笔记多为图集，也可能是视频）
const { httpGet, resolveRedirect } = require('../lib/http');
const { videoResult, imageResult } = require('../lib/result');
const { meta, metaAll } = require('./meta');

const platform = 'xiaohongshu';

function match(u) {
  return /xhslink|xiaohongshu\.com|xhs/.test(u);
}

async function parse(url) {
  const real = await resolveRedirect(url);
  const html = (await httpGet(real)).body;

  const title = meta(html, 'og:title') || '小红书笔记';

  const video = meta(html, 'og:video') || meta(html, 'og:video:url');
  if (video) return videoResult({ platform, title, url: video, cover: meta(html, 'og:image') });

  // 图集：og:image 可能有多张
  let images = metaAll(html, 'og:image');
  if (!images.length) {
    const m = html.match(/"(https?:[^"']*?(?:sns-img|xhscdn)[^"']*?\.(?:jpg|jpeg|png|webp))[^"']*"/g);
    if (m) images = m.map((x) => x.replace(/^"|"$/g, '').replace(/\\u002F/g, '/'));
  }
  if (images.length) return imageResult({ platform, title, images });

  throw new Error('xiaohongshu parse failed');
}

module.exports = { platform, match, parse };
