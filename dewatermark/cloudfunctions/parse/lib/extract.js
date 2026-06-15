// 从 HTML/JSON 文本里抠出媒体直链的通用小工具
function unescapeUrl(u) {
  return String(u || '')
    .replace(/\\u002[fF]/g, '/')
    .replace(/\\u0026/g, '&')
    .replace(/\\\//g, '/')
    .replace(/&amp;/g, '&');
}

// JSON 字符串体匹配片段：(?:\\.|[^"\\])*  —— 能吃掉 / 这类转义
const STR = '((?:\\\\.|[^"\\\\])*)';

// 找出第一个 mp4 直链（兼容 /、\/、/ 转义写法）
function firstMp4(html) {
  const m = String(html || '').match(/https?:[^"'\s]*?\.mp4[^"'\s]*/i);
  return m ? unescapeUrl(m[0]) : '';
}

// 按字段名在 JSON 文本里找第一个该字段对应的 http(s) 链接（字段值为字符串）
function firstFieldUrl(text, fields) {
  const s = String(text || '');
  for (const f of fields) {
    const re = new RegExp('"' + f + '"\\s*:\\s*"' + STR + '"', 'i');
    const m = s.match(re);
    if (m) {
      const url = unescapeUrl(m[1]);
      if (/^https?:/i.test(url)) return url;
    }
  }
  return '';
}

// 找第一个 url_list 数组里的首个链接（短视频结构常见：play_addr/download_addr.url_list[0]）
function firstUrlList(text) {
  const m = String(text || '').match(new RegExp('"url_list"\\s*:\\s*\\[\\s*"' + STR + '"', 'i'));
  if (!m) return '';
  const url = unescapeUrl(m[1]);
  return /^https?:/i.test(url) ? url : '';
}

module.exports = { unescapeUrl, firstMp4, firstFieldUrl, firstUrlList };
