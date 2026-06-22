// 爆款工厂 · 本地规则引擎：不配任何模型 Key 也能走通「商品 → 广告脚本 → 画面 → 口播片」全流程
// 生成式 SVG 占位图 + SMIL 动画占位视频，界面明确标注「本地生成」。接入模型后自动切换为真实生成。
import fs from 'node:fs';
import path from 'node:path';
import { UPLOAD_DIR } from './db.js';
import { hashCode, seededRandom, escapeXML, ratioSize, uid } from './util.js';

const PALETTES = [[222, 264], [328, 18], [158, 196], [22, 44], [268, 318], [188, 152]];

function svgWrap(w, h, inner) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${inner}</svg>`;
}
function defs(rnd, id, [h1, h2]) {
  return `<defs>
  <linearGradient id="bg${id}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="hsl(${h1},55%,${16 + rnd() * 8}%)"/>
    <stop offset="1" stop-color="hsl(${h2},60%,${34 + rnd() * 10}%)"/>
  </linearGradient>
  <radialGradient id="spot${id}" cx="0.5" cy="0.38" r="0.62">
    <stop offset="0" stop-color="hsl(${h2},85%,82%)" stop-opacity="0.7"/>
    <stop offset="1" stop-color="hsl(${h1},60%,18%)" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="prod${id}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="hsl(${h2},70%,72%)"/>
    <stop offset="1" stop-color="hsl(${h1},65%,46%)"/>
  </linearGradient>
</defs>`;
}
const fontFam = `system-ui,'PingFang SC','Microsoft YaHei',sans-serif`;
const badge = (w, h, label) =>
  `<g opacity="0.9"><rect x="${w - 180}" y="${h - 38}" rx="12" width="164" height="24" fill="rgba(0,0,0,0.5)"/>
   <text x="${w - 98}" y="${h - 21}" font-size="12" fill="rgba(255,255,255,0.92)" text-anchor="middle" font-family="${fontFam}">爆款工厂 · 本地生成 ${escapeXML(label)}</text></g>`;

/** 产品造型：一个被打光的盒子/瓶子，桌面反光 */
function productArt(rnd, w, h, id) {
  const cx = w / 2, cy = h * 0.42;
  const pw = w * 0.34, ph = h * 0.24;
  return `
  <ellipse cx="${cx}" cy="${cy + ph * 0.62}" rx="${pw * 0.7}" ry="${ph * 0.12}" fill="rgba(0,0,0,0.45)"/>
  <rect x="${cx - pw / 2}" y="${cy - ph / 2}" width="${pw}" height="${ph}" rx="${pw * 0.08}" fill="url(#prod${id})" stroke="rgba(255,255,255,0.45)" stroke-width="2"/>
  <rect x="${cx - pw / 2}" y="${cy - ph / 2}" width="${pw * 0.34}" height="${ph}" rx="${pw * 0.08}" fill="rgba(255,255,255,0.14)"/>
  <circle cx="${cx + pw * 0.18}" cy="${cy}" r="${ph * 0.2}" fill="rgba(255,255,255,0.85)" opacity="0.5"/>`;
}
/** 数字人/达人剪影（UGC 口播占位） */
function presenterArt(w, h, hue) {
  const cx = w * 0.5, cy = h * 0.34;
  return `
  <circle cx="${cx}" cy="${cy - h * 0.04}" r="${h * 0.066}" fill="rgba(12,16,30,0.9)" stroke="hsl(${hue},70%,70%)" stroke-width="3"/>
  <path d="M ${cx - w * 0.16} ${h * 0.62} Q ${cx} ${cy + h * 0.06} ${cx + w * 0.16} ${h * 0.62} L ${cx + w * 0.2} ${h * 0.78} L ${cx - w * 0.2} ${h * 0.78} Z"
        fill="rgba(12,16,30,0.9)" stroke="hsl(${hue},70%,70%)" stroke-width="3"/>
  <circle cx="${cx - w * 0.026}" cy="${cy - h * 0.05}" r="3.6" fill="hsl(${hue},85%,80%)"/>
  <circle cx="${cx + w * 0.026}" cy="${cy - h * 0.05}" r="3.6" fill="hsl(${hue},85%,80%)"/>
  <path d="M ${cx - w * 0.022} ${cy - h * 0.028} Q ${cx} ${cy - h * 0.012} ${cx + w * 0.022} ${cy - h * 0.028}" stroke="hsl(${hue},85%,80%)" stroke-width="2.6" fill="none" stroke-linecap="round"/>`;
}

function wrapText(s, per) {
  const t = String(s || ''); const out = [];
  for (let i = 0; i < t.length && out.length < 3; i += per) out.push(t.slice(i, i + per));
  return out;
}
function onscreenBlock(w, h, text) {
  const lines = wrapText(text, Math.max(8, Math.floor(w / 42)));
  const fs0 = Math.round(w / 16);
  return lines.map((ln, i) =>
    `<text x="${w / 2}" y="${h * 0.84 + i * fs0 * 1.2}" font-size="${fs0}" font-weight="800" fill="#fff"
      text-anchor="middle" font-family="${fontFam}" stroke="rgba(0,0,0,0.55)" stroke-width="${fs0 * 0.08}" paint-order="stroke">${escapeXML(ln)}</text>`
  ).join('');
}

/** 一帧静图：商品卡（kind: product|presenter） */
export function localFrameSVG({ onscreen = '', brand = '', price = '', kind = 'product', ratio = '9:16', order = 0 }) {
  const seed = hashCode(kind + onscreen + brand + order);
  const rnd = seededRandom(seed);
  const pal = PALETTES[seed % PALETTES.length];
  const id = (seed % 9973).toString(36);
  const { w, h } = ratioSize(ratio, 1080);
  const art = kind === 'presenter' ? presenterArt(w, h, pal[1]) : productArt(rnd, w, h, id);
  const tag = brand ? `<text x="28" y="${Math.round(h * 0.07)}" font-size="${Math.round(w / 28)}" font-weight="800" fill="rgba(255,255,255,0.92)" font-family="${fontFam}">${escapeXML(brand)}</text>` : '';
  const priceTag = price ? `<g><rect x="${w - 168}" y="22" rx="20" width="146" height="44" fill="#ff3b6b"/><text x="${w - 95}" y="51" font-size="${Math.round(w / 30)}" font-weight="800" fill="#fff" text-anchor="middle" font-family="${fontFam}">${escapeXML(price)}</text></g>` : '';
  const inner = `${defs(rnd, id, pal)}
  <rect width="${w}" height="${h}" fill="url(#bg${id})"/>
  <rect width="${w}" height="${h}" fill="url(#spot${id})"/>
  ${art}${tag}${priceTag}
  ${onscreenBlock(w, h, onscreen)}
  ${badge(w, h, '商品图')}`;
  return svgWrap(w, h, inner);
}

/** 一段"视频"：SMIL 动画（缓推 + 光斑流动 + 字幕 + 进度条），<img> 可直接播放 */
export function localClipSVG({ onscreen = '', voiceover = '', brand = '', kind = 'product', ratio = '9:16', duration = 5, order = 0 }) {
  const seed = hashCode('v' + onscreen + voiceover + order);
  const rnd = seededRandom(seed);
  const pal = PALETTES[seed % PALETTES.length];
  const id = (seed % 9973).toString(36);
  const { w, h } = ratioSize(ratio, 1080);
  const dur = Math.min(12, Math.max(2, duration));
  const art = kind === 'presenter' ? presenterArt(w, h, pal[1]) : productArt(rnd, w, h, id);
  const inner = `${defs(rnd, id, pal)}
  <rect width="${w}" height="${h}" fill="url(#bg${id})"/>
  <g>
    <animateTransform attributeName="transform" type="scale" values="1;1.06;1" dur="${dur * 2}s" repeatCount="indefinite" additive="sum"/>
    <rect width="${w}" height="${h}" fill="url(#spot${id})"/>
    ${art}
  </g>
  <circle r="${h * 0.26}" fill="hsl(${pal[1]},85%,72%)" opacity="0.14">
    <animate attributeName="cx" values="${-w * 0.2};${w * 1.2}" dur="${dur}s" repeatCount="indefinite"/>
    <animate attributeName="cy" values="${h * 0.3};${h * 0.5}" dur="${dur}s" repeatCount="indefinite"/>
  </circle>
  <text x="24" y="${Math.round(h * 0.05)}" font-size="${Math.round(w / 40)}" fill="rgba(255,255,255,0.82)" font-family="ui-monospace,monospace">SHOT ${String(order || 1).padStart(2, '0')} · ${dur}s · LOCAL PREVIEW</text>
  ${onscreenBlock(w, h, onscreen)}
  <rect x="0" y="${h - 6}" height="6" fill="hsl(${pal[1]},85%,65%)" width="0"><animate attributeName="width" values="0;${w}" dur="${dur}s" repeatCount="indefinite"/></rect>
  ${badge(w, h, '口播预览')}`;
  return svgWrap(w, h, inner);
}

export function saveSVG(svg) {
  const name = `${uid('loc')}.svg`;
  fs.writeFileSync(path.join(UPLOAD_DIR, name), svg, 'utf8');
  return `/uploads/${name}`;
}
