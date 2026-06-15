// 快手解析：分享页 og 标签 / 内联 mp4 直链
const { httpGet, resolveRedirect } = require('../lib/http');
const { videoResult } = require('../lib/result');
const { meta } = require('./meta');

const platform = 'kuaishou';

function match(u) {
  return /kuaishou\.com|kwai|chenzhongtech|gifshow/.test(u);
}

async function parse(url) {
  const real = await resolveRedirect(url);
  const html = (await httpGet(real)).body;

  const title = meta(html, 'og:title') || '快手作品';
  const cover = meta(html, 'og:image');

  let video = meta(html, 'og:video') || meta(html, 'og:video:url') || meta(html, 'og:video:secure_url');
  if (!video) {
    const m = html.match(/"(https?:[^"']*?\.mp4[^"']*)"/);
    if (m) video = m[1].replace(/\\u002F/g, '/');
  }
  if (!video) throw new Error('kuaishou parse failed');

  return videoResult({ platform, title, url: video, cover });
}

module.exports = { platform, match, parse };
