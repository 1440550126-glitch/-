// 从 HTML 里提取 <meta property/name="..." content="..."> 的小工具
function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function meta(html, prop) {
  const p = escapeRe(prop);
  const re = new RegExp(
    '<meta[^>]+(?:property|name)=["\']' + p + '["\'][^>]*content=["\']([^"\']+)["\']',
    'i'
  );
  const m = html.match(re);
  if (m) return m[1];
  // content 在 property 之前的写法
  const re2 = new RegExp(
    '<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']' + p + '["\']',
    'i'
  );
  const m2 = html.match(re2);
  return m2 ? m2[1] : '';
}

function metaAll(html, prop) {
  const p = escapeRe(prop);
  const re = new RegExp(
    '<meta[^>]+(?:property|name)=["\']' + p + '["\'][^>]*content=["\']([^"\']+)["\']',
    'ig'
  );
  const out = [];
  let m;
  while ((m = re.exec(html))) out.push(m[1]);
  return out;
}

module.exports = { meta, metaAll };
