// 爆款工厂 · 电商商品解析：商品页 URL → 结构化商品信息（标题/品牌/价格/主图/卖点）
// 只读取公开页面的 <meta og:*> / JSON-LD(Product) / <title>，不做登录态抓取、不绕过反爬，规避合规风险。
// 抓不到时回退到「手填商品信息」。parseProductHtml 为纯函数，便于离线测试。

function decodeEntities(s = '') {
  return String(s)
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&nbsp;/g, ' ')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n)).trim();
}
function metaContent(html, attr, val) {
  // <meta property="og:title" content="..."> 任意属性顺序
  const re = new RegExp(`<meta[^>]+(?:property|name)=["']${val}["'][^>]*content=["']([^"']*)["']`, 'i');
  const re2 = new RegExp(`<meta[^>]+content=["']([^"']*)["'][^>]*(?:property|name)=["']${val}["']`, 'i');
  return decodeEntities((html.match(re) || html.match(re2) || [])[1] || '');
}
function allMeta(html, val) {
  const out = [];
  const re = new RegExp(`<meta[^>]+(?:property|name)=["']${val}["'][^>]*content=["']([^"']*)["']`, 'ig');
  let m; while ((m = re.exec(html))) out.push(decodeEntities(m[1]));
  return out;
}

/** 从 HTML 文本抽取商品信息（纯函数）。返回 {title,brand,price,currency,images[],desc,points[]} */
export function parseProductHtml(html = '', url = '') {
  const h = String(html);
  let title = metaContent(h, 'p', 'og:title') || metaContent(h, 'n', 'twitter:title');
  if (!title) title = decodeEntities((h.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || '');
  const desc = metaContent(h, 'p', 'og:description') || metaContent(h, 'n', 'description');
  const images = [...new Set([
    ...allMeta(h, 'og:image'), ...allMeta(h, 'og:image:secure_url'), ...allMeta(h, 'twitter:image')
  ])].filter(Boolean).slice(0, 6);
  let brand = metaContent(h, 'p', 'og:site_name') || metaContent(h, 'p', 'product:brand');
  let price = metaContent(h, 'p', 'product:price:amount') || metaContent(h, 'p', 'og:price:amount');
  let currency = metaContent(h, 'p', 'product:price:currency') || metaContent(h, 'p', 'og:price:currency');

  // JSON-LD（schema.org/Product）
  for (const m of h.matchAll(/<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/ig)) {
    try {
      const json = JSON.parse(m[1].trim());
      const arr = Array.isArray(json) ? json : (json['@graph'] || [json]);
      for (const node of arr) {
        const t = node && (Array.isArray(node['@type']) ? node['@type'] : [node['@type']]);
        if (t && t.includes('Product')) {
          title = title || node.name;
          brand = brand || (typeof node.brand === 'string' ? node.brand : node.brand?.name) || '';
          const offer = Array.isArray(node.offers) ? node.offers[0] : node.offers;
          if (offer) { price = price || String(offer.price ?? offer.lowPrice ?? ''); currency = currency || offer.priceCurrency || ''; }
          if (node.image) for (const im of [].concat(node.image)) if (im && !images.includes(im)) images.push(im);
        }
      }
    } catch { /* 忽略坏的 JSON-LD */ }
  }

  // 卖点：取描述的分句 + 常见列表项
  const points = [];
  if (desc) for (const seg of desc.split(/[。.;；·•\n\|]/).map((s) => s.trim()).filter((s) => s.length >= 4 && s.length <= 40)) {
    if (points.length < 5 && !points.includes(seg)) points.push(seg);
  }
  return {
    url, title: (title || '').slice(0, 120), brand: (brand || '').slice(0, 40),
    price: (price || '').replace(/[^\d.]/g, '').slice(0, 12), currency: (currency || '').slice(0, 6),
    images: images.slice(0, 6), desc: (desc || '').slice(0, 400), points
  };
}

/** 抓取商品页（公开 OG/JSON-LD）。失败抛错，调用方应回退到手填。 */
export async function scrapeProduct(url) {
  const u = String(url || '').trim();
  if (!/^https?:\/\//i.test(u)) throw new Error('请填写以 http(s):// 开头的商品页链接');
  let resp;
  try {
    resp = await fetch(u, {
      redirect: 'follow', signal: AbortSignal.timeout(15_000),
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; TopViewBot/0.1; +https://example.com/bot)', 'Accept': 'text/html' }
    });
  } catch (e) {
    throw new Error(`抓取失败（${e.name === 'TimeoutError' ? '超时' : '网络不可达'}）：可改用「手填商品信息」`);
  }
  if (!resp.ok) throw new Error(`抓取失败 HTTP ${resp.status}：可改用「手填商品信息」`);
  const html = (await resp.text()).slice(0, 800_000);
  const p = parseProductHtml(html, u);
  if (!p.title) throw new Error('页面未暴露公开商品信息（og/JSON-LD），请改用「手填商品信息」');
  return p;
}

/** 归一化手填 / 抓取的商品信息 */
export function normalizeProduct(p = {}) {
  const points = (Array.isArray(p.points) ? p.points : String(p.points || '').split(/[\n,，;；]/))
    .map((s) => String(s).trim()).filter(Boolean).slice(0, 6);
  const images = (Array.isArray(p.images) ? p.images : String(p.images || '').split(/[\n,，\s]/))
    .map((s) => String(s).trim()).filter(Boolean).slice(0, 6);
  return {
    url: String(p.url || '').slice(0, 500),
    title: String(p.title || '').slice(0, 120),
    brand: String(p.brand || '').slice(0, 40),
    price: String(p.price || '').slice(0, 16),
    currency: String(p.currency || '').slice(0, 6),
    desc: String(p.desc || '').slice(0, 400),
    points, images
  };
}
