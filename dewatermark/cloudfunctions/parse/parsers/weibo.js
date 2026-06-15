// 微博解析：分享页 og 标签 / 内联 stream_url / mp4 直链；图文则取 og:image
const { httpGet, resolveRedirect } = require('../lib/http');
const { videoResult, imageResult } = require('../lib/result');
const { meta, metaAll } = require('./meta');
const { firstMp4, firstFieldUrl } = require('../lib/extract');

const platform = 'weibo';

function match(u) {
  return /weibo\.(com|cn)|video\.weibo|t\.cn|miaopai/.test(u);
}

async function parse(url) {
  const real = await resolveRedirect(url);
  const html = (await httpGet(real, { headers: { Referer: 'https://weibo.com/' } })).body;

  const title = meta(html, 'og:title') || '微博内容';
  const cover = meta(html, 'og:image');

  let video =
    meta(html, 'og:video') ||
    meta(html, 'og:video:url') ||
    firstFieldUrl(html, ['stream_url_hd', 'stream_url', 'mp4_hd_url', 'mp4_sd_url']) ||
    firstMp4(html);

  if (video) return videoResult({ platform, title, url: video, cover });

  const images = metaAll(html, 'og:image');
  if (images.length) return imageResult({ platform, title, images });

  throw new Error('weibo parse failed');
}

module.exports = { platform, match, parse };
