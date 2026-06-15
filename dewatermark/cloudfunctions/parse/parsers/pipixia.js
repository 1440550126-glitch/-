// 皮皮虾解析（字节系，结构近似抖音）：分享页内联 play_addr / mp4 直链
const { httpGet, resolveRedirect } = require('../lib/http');
const { videoResult } = require('../lib/result');
const { meta } = require('./meta');
const { firstMp4, firstUrlList, unescapeUrl } = require('../lib/extract');

const platform = 'pipixia';

function match(u) {
  return /pipix\.com|pipixia/.test(u);
}

function noWatermark(u) {
  return u.replace('/playwm/', '/play/').replace('playwm', 'play').replace(/watermark=1/g, 'watermark=0');
}

async function parse(url) {
  const real = await resolveRedirect(url);
  const html = (await httpGet(real)).body;

  const title = meta(html, 'og:title') || '皮皮虾视频';
  const cover = meta(html, 'og:image');

  // play_addr / download_addr.url_list 首个，或直接 mp4
  let video = firstUrlList(html) || firstMp4(html);

  if (!video) throw new Error('pipixia parse failed');
  video = noWatermark(unescapeUrl(video));
  return videoResult({ platform, title, url: video, cover });
}

module.exports = { platform, match, parse };
