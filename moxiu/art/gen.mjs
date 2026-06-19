// 《墨修》水墨美术生成器
// 纯手绘 SVG（矢量笔触 + 水墨晕染滤镜 + 宣纸纹理），渲染成 PNG 预览。
// 用法: node gen.mjs [char|scene|start|all]
import { render, FONTS } from './lib.mjs';
import { cultivator } from './char.mjs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const OUT = dirname(fileURLToPath(import.meta.url));

/* ============================== 调色盘 ============================== */
const C = {
  paper:   '#efe7d6',   // 宣纸
  paperHi: '#f6f0e2',   // 高光纸
  paperLo: '#e2d7c0',   // 纸暗角
  ink:     '#282f34',   // 浓墨（偏冷的近黑）
  ink2:    '#4d565c',   // 中墨
  ink3:    '#8c9498',   // 淡墨
  inkFar:  '#aab0ad',   // 远山墨
  mist:    '#f4eee0',   // 云雾/留白
  skin:    '#f1e3cf',   // 肤
  skinSh:  '#e4cdae',   // 肤阴影
  robe:    '#ece3d1',   // 袍（浅）
  robeSh:  '#d6cab0',   // 袍阴影
  hair:    '#20262b',   // 发
  cinnabar:'#b1402f',   // 朱砂（印章/剑穗）
  indigo:  '#3c5666',   // 石青（腰带/点缀）
  gold:    '#c79a4e',   // 描金
  blade:   '#dde2e1',   // 剑身
};

/* ============================== 共享滤镜/渐变 ============================== */
const DEFS = `
<defs>
  <!-- 宣纸纤维纹理 -->
  <filter id="paper" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="11" result="n"/>
    <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.045 0"/>
    <feComposite operator="over" in2="SourceGraphic"/>
  </filter>
  <!-- 湿笔晕染：把规整边缘打散成水墨化开的边 -->
  <filter id="wet" x="-25%" y="-25%" width="150%" height="150%">
    <feTurbulence type="fractalNoise" baseFrequency="0.013 0.02" numOctaves="2" seed="4" result="t"/>
    <feDisplacementMap in="SourceGraphic" in2="t" scale="20" xChannelSelector="R" yChannelSelector="G" result="d"/>
    <feGaussianBlur in="d" stdDeviation="0.8"/>
  </filter>
  <filter id="wetSoft" x="-30%" y="-30%" width="160%" height="160%">
    <feTurbulence type="fractalNoise" baseFrequency="0.02 0.03" numOctaves="2" seed="9" result="t"/>
    <feDisplacementMap in="SourceGraphic" in2="t" scale="9" xChannelSelector="R" yChannelSelector="G" result="d"/>
    <feGaussianBlur in="d" stdDeviation="0.5"/>
  </filter>
  <!-- 雾气柔化 -->
  <!-- 山脊湿边（仅高斯，避免大图位移崩溃） -->
  <filter id="mtnEdge" x="-8%" y="-8%" width="116%" height="116%"><feGaussianBlur stdDeviation="1.7"/></filter>
  <filter id="mist" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
  <filter id="mistBig" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="26"/></filter>
  <!-- 人物落地投影 -->
  <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
  <!-- 远山渐隐（上淡下浓，模拟空气透视的反向：山头入雾） -->
  <linearGradient id="mtnFar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="${C.inkFar}" stop-opacity="0"/>
    <stop offset="0.5" stop-color="${C.inkFar}" stop-opacity="0.5"/>
    <stop offset="1" stop-color="${C.ink3}" stop-opacity="0.75"/>
  </linearGradient>
  <linearGradient id="mtnMid" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="${C.ink3}" stop-opacity="0.15"/>
    <stop offset="1" stop-color="${C.ink2}" stop-opacity="0.9"/>
  </linearGradient>
  <linearGradient id="mtnNear" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="${C.ink2}" stop-opacity="0.5"/>
    <stop offset="1" stop-color="${C.ink}" stop-opacity="0.97"/>
  </linearGradient>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="${C.paperHi}"/>
    <stop offset="0.55" stop-color="${C.paper}"/>
    <stop offset="1" stop-color="${C.paperLo}"/>
  </linearGradient>
  <radialGradient id="bladeG" cx="0.5" cy="0.2" r="0.9">
    <stop offset="0" stop-color="#f3f5f4"/><stop offset="1" stop-color="${C.blade}"/>
  </radialGradient>
  <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="${C.paperHi}" stop-opacity="0.9"/>
    <stop offset="1" stop-color="${C.paperHi}" stop-opacity="0"/>
  </radialGradient>
</defs>`;

/* ============================== 场景元件 ============================== */

// 宣纸底 + 四角暗
function paper(w, h) {
  return `<rect width="${w}" height="${h}" fill="url(#sky)"/>
  <rect width="${w}" height="${h}" fill="${C.paper}" filter="url(#paper)" opacity="0.6"/>
  <radialGradient id="vig" cx="0.5" cy="0.42" r="0.75">
    <stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#5b4a2e" stop-opacity="0.16"/>
  </radialGradient>
  <rect width="${w}" height="${h}" fill="url(#vig)"/>`;
}

// 一道山脊：平滑峰线 + 微抖动笔触感 + 渐变填充，填到画布底，柔化湿边
function ridge(pts, fill, { op = 1, bottom = 1200 } = {}) {
  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 1; i < pts.length; i++) {
    const [x, y] = pts[i], [px, py] = pts[i - 1];
    const cx = (px + x) / 2;
    const j = ((i * 37) % 9) - 4;                 // 峰线微抖动，像手绘
    d += ` Q ${px} ${(py + j).toFixed(1)} ${cx} ${((py + y) / 2).toFixed(1)}`;
  }
  const last = pts[pts.length - 1];
  d += ` L ${last[0]} ${bottom} L ${pts[0][0]} ${bottom} Z`;
  return `<path d="${d}" fill="${fill}" opacity="${op}" filter="url(#mtnEdge)"/>`;
}

// 云雾带
function mistBand(x, y, w, h, op = 0.85, big = false) {
  return `<ellipse cx="${x}" cy="${y}" rx="${w}" ry="${h}" fill="${C.mist}" opacity="${op}" filter="url(#${big ? 'mistBig' : 'mist'})"/>`;
}

// 远飞鸟（“人”字）
function birds(x, y, n = 4, s = 1) {
  let g = '';
  for (let i = 0; i < n; i++) {
    const bx = x + i * 26 * s + (i % 2) * 6, by = y + Math.sin(i) * 12 * s - i * 4;
    const w = 9 * s;
    g += `<path d="M ${bx - w} ${by} Q ${bx} ${by - w * 0.7} ${bx} ${by} Q ${bx} ${by - w * 0.7} ${bx + w} ${by}" stroke="${C.ink2}" stroke-width="${1.6 * s}" fill="none" stroke-linecap="round" opacity="0.7"/>`;
  }
  return g;
}

// 松树（近景框景）
function pine(x, y, s = 1, flip = false) {
  const f = flip ? -1 : 1;
  const trunk = `<path d="M ${x} ${y} q ${8 * f} ${-60} ${2 * f} ${-120} q ${-4 * f} ${-40} ${6 * f} ${-70}"
    stroke="${C.ink}" stroke-width="${7 * s}" fill="none" stroke-linecap="round" filter="url(#wetSoft)"/>`;
  // 层叠墨叶团（松冠）：扁椭圆色块 + 短针叶纹理
  let foliage = '';
  const pads = [[6 * f, -205, 40], [-22 * f, -168, 36], [30 * f, -150, 38], [2 * f, -132, 34], [-18 * f, -104, 30], [26 * f, -96, 28]];
  for (const [dx, dy, r] of pads) {
    const cx = x + dx * s, cy = y + dy * s, rr = r * s;
    foliage += `<ellipse cx="${cx.toFixed(0)}" cy="${cy.toFixed(0)}" rx="${rr.toFixed(0)}" ry="${(rr * 0.5).toFixed(0)}" fill="${C.ink2}" opacity="0.7" filter="url(#wetSoft)"/>`;
    foliage += `<ellipse cx="${cx.toFixed(0)}" cy="${(cy + rr * 0.12).toFixed(0)}" rx="${(rr * 0.66).toFixed(0)}" ry="${(rr * 0.32).toFixed(0)}" fill="${C.ink}" opacity="0.55"/>`;
    for (let i = 0; i < 7; i++) {
      const tx = cx - rr + (i * 2 * rr) / 6;
      foliage += `<line x1="${tx.toFixed(0)}" y1="${(cy + 2).toFixed(0)}" x2="${(tx).toFixed(0)}" y2="${(cy + rr * 0.5 + 4).toFixed(0)}" stroke="${C.ink}" stroke-width="${1.2 * s}" stroke-linecap="round" opacity="0.5"/>`;
    }
  }
  return trunk + foliage;
}

// 红印章
function seal(x, y, size, ch, font = FONTS.brush) {
  return `<g>
    <rect x="${x}" y="${y}" width="${size}" height="${size}" rx="${size * 0.08}" fill="${C.cinnabar}" filter="url(#wetSoft)"/>
    <text x="${x + size / 2}" y="${y + size * 0.74}" font-family="${font}" font-size="${size * 0.7}" fill="${C.paperHi}" text-anchor="middle">${ch}</text>
  </g>`;
}

/* ============================== 角色：Q版水墨修士 ==============================
   局部坐标 0..240 (宽) × 0..340 (高)，脚底约 y=312，头顶发髻约 y=18 */
function _cultivatorOld({ x = 0, y = 0, scale = 1, gender = 'female', withGround = true } = {}) {
  const female = gender === 'female';
  const accent = female ? C.indigo : C.cinnabar;     // 腰带主色
  const robe = female ? '#efe7d6' : '#e4dccb';       // 男装稍灰
  const robeSh = female ? '#dcd2bd' : '#cfc4aa';
  const O = C.ink, OW = 2.6;                          // 主轮廓
  const FW = 1.5;                                     // 衣纹细线

  // —— 落地墨晕 ——
  const ground = withGround
    ? `<ellipse cx="120" cy="318" rx="86" ry="17" fill="${C.ink}" opacity="0.22" filter="url(#wet)"/>
       <ellipse cx="120" cy="316" rx="54" ry="9" fill="${C.ink}" opacity="0.3" filter="url(#wetSoft)"/>`
    : '';

  // —— 云头履（脚，藏在下摆下） ——
  const feet = `<path d="M 96 306 q -10 2 -14 10 q 0 6 8 6 l 18 0 0 -16 Z" fill="${C.ink2}" stroke="${O}" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M 144 306 q 10 2 14 10 q 0 6 -8 6 l -18 0 0 -16 Z" fill="${C.ink2}" stroke="${O}" stroke-width="1.6" stroke-linejoin="round"/>`;

  // —— 飘带（身后一缕，极淡，仅为灵动） ——
  const ribbon = `<path d="M 150 196 q 60 34 44 96 q -8 30 14 56 q -28 -8 -34 -46 q -6 -42 -38 -82 Z"
      fill="${accent}" opacity="0.12" filter="url(#wetSoft)"/>`;

  // —— 背发（短，藏在肩后，仅作底衬） ——
  const backHair = female
    ? `<path d="M 86 118 q -18 36 -10 78 q 4 18 16 26 q -20 -2 -26 -28 q -6 -46 8 -78 Z" fill="${C.hair}" opacity="0.92"/>
       <path d="M 154 118 q 18 36 10 78 q -4 18 -16 26 q 20 -2 26 -28 q 6 -46 -8 -78 Z" fill="${C.hair}" opacity="0.92"/>`
    : '';

  // —— 身前两缕长发（女，飘逸地垂在袍前） ——
  const frontLocks = female
    ? `<path d="M 92 138 q -10 50 -4 96 q 2 14 -4 24 q -10 -8 -10 -26 q -2 -50 8 -96 Z" fill="${C.hair}" filter="url(#wetSoft)"/>
       <path d="M 148 138 q 10 50 4 96 q -2 14 4 24 q 10 -8 10 -26 q 2 -50 -8 -96 Z" fill="${C.hair}" filter="url(#wetSoft)"/>`
    : '';

  // —— 道袍主体 ——
  const robeBody = `
    <path d="M 86 150
             C 70 156 60 168 52 196
             C 44 224 40 262 42 296
             Q 60 290 78 294
             Q 80 300 84 312
             L 120 314 L 156 312
             Q 160 300 162 294
             Q 180 290 198 296
             C 200 262 196 224 188 196
             C 180 168 170 156 154 150
             Q 120 138 86 150 Z"
          fill="${robe}" stroke="${O}" stroke-width="${OW}" stroke-linejoin="round"/>
    <!-- 下摆暗部水墨 -->
    <path d="M 46 286 Q 120 304 194 286 L 192 300 Q 120 318 48 300 Z" fill="${robeSh}" opacity="0.8" filter="url(#wetSoft)"/>
    <!-- 衣纹 -->
    <path d="M 96 168 q -10 60 -8 126" stroke="${robeSh}" stroke-width="${FW}" fill="none" opacity="0.8"/>
    <path d="M 144 168 q 10 60 8 126" stroke="${robeSh}" stroke-width="${FW}" fill="none" opacity="0.8"/>
    <path d="M 120 176 l 0 132" stroke="${robeSh}" stroke-width="${FW}" fill="none" opacity="0.6"/>`;

  // —— 交领右衽 ——
  const collar = `
    <path d="M 92 150 Q 120 176 120 176 Q 120 176 150 150
             L 142 158 Q 120 184 120 184 Q 120 184 100 158 Z"
          fill="${robeSh}" stroke="${O}" stroke-width="${OW * 0.8}" stroke-linejoin="round"/>
    <path d="M 120 176 L 120 200" stroke="${O}" stroke-width="1.4" opacity="0.5"/>`;

  // —— 大袖（左右） ——
  const sleeves = `
    <path d="M 86 152 C 58 158 42 184 38 214 C 36 230 44 240 58 240 C 60 218 70 188 92 170 Z"
          fill="${robe}" stroke="${O}" stroke-width="${OW}" stroke-linejoin="round"/>
    <path d="M 154 152 C 182 158 198 184 202 214 C 204 230 196 240 182 240 C 180 218 170 188 148 170 Z"
          fill="${robe}" stroke="${O}" stroke-width="${OW}" stroke-linejoin="round"/>
    <path d="M 50 220 q 10 -26 30 -46" stroke="${robeSh}" stroke-width="${FW}" fill="none" opacity="0.8"/>
    <path d="M 190 220 q -10 -26 -30 -46" stroke="${robeSh}" stroke-width="${FW}" fill="none" opacity="0.8"/>`;

  // —— 腰带 + 结 + 飘穗 ——
  const belt = `
    <path d="M 78 224 Q 120 236 162 224 L 160 244 Q 120 256 80 244 Z" fill="${accent}" stroke="${O}" stroke-width="1.6" filter="url(#wetSoft)"/>
    <path d="M 112 232 q 8 6 16 0 q 2 10 -8 12 q -10 -2 -8 -12 Z" fill="${accent}" stroke="${O}" stroke-width="1.2"/>
    <path d="M 114 244 q -6 36 -2 60" stroke="${accent}" stroke-width="5" fill="none" stroke-linecap="round" filter="url(#wetSoft)"/>
    <path d="M 126 244 q 8 34 4 58" stroke="${accent}" stroke-width="5" fill="none" stroke-linecap="round" filter="url(#wetSoft)"/>`;

  // —— 剑（左手持，剑尖朝上） ——
  const sword = `
    <g>
      <line x1="78" y1="208" x2="60" y2="60" stroke="${O}" stroke-width="9" stroke-linecap="round"/>
      <path d="M 80 206 L 61 58 L 54 60 L 74 208 Z" fill="url(#bladeG)" stroke="${C.ink2}" stroke-width="1"/>
      <line x1="67" y1="64" x2="77" y2="202" stroke="#fff" stroke-width="1.2" opacity="0.7"/>
      <!-- 剑格 -->
      <path d="M 69 205 l 20 7 -2 8 -20 -7 Z" fill="${C.gold}" stroke="${O}" stroke-width="1.4"/>
      <!-- 剑柄 + 手 -->
      <rect x="74" y="210" width="12" height="24" rx="4" transform="rotate(8 80 222)" fill="${C.ink2}" stroke="${O}" stroke-width="1.4"/>
      <ellipse cx="84" cy="222" rx="10.5" ry="8.5" fill="${C.skin}" stroke="${O}" stroke-width="1.8"/>
      <!-- 剑穗（绳结 + 双流苏） -->
      <circle cx="80" cy="214" r="3" fill="${C.cinnabar}"/>
      <path d="M 80 216 q -12 18 -8 40 M 80 216 q -2 20 -10 38" stroke="${C.cinnabar}" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M 64 252 q 6 12 0 22 M 70 254 q 5 11 -1 20" stroke="${C.cinnabar}" stroke-width="5" fill="none" stroke-linecap="round" filter="url(#wetSoft)"/>
    </g>`;

  // —— 远手（袖中） ——
  const farHand = `<ellipse cx="170" cy="236" rx="9" ry="7" fill="${C.skin}" stroke="${O}" stroke-width="1.6"/>`;

  // —— 头 ——
  const head = `<circle cx="120" cy="96" r="50" fill="${C.skin}" stroke="${O}" stroke-width="${OW}"/>`;

  // —— 头发 ——
  const hairTop = `
    <path d="M 72 96 C 66 50 92 22 120 22 C 148 22 174 50 168 96
             C 160 78 150 70 150 70 C 150 70 156 86 150 92
             C 142 74 128 68 128 68 L 120 80 L 112 68
             C 112 68 98 74 90 92 C 84 86 90 70 90 70 C 90 70 80 78 72 96 Z"
          fill="${C.hair}"/>
    <!-- 发髻 -->
    <ellipse cx="120" cy="34" rx="20" ry="15" fill="${C.hair}" stroke="${C.ink}" stroke-width="1"/>
    <ellipse cx="120" cy="32" rx="9" ry="7" fill="#2c343a"/>
    <!-- 簪 -->
    <line x1="${female ? 104 : 100}" y1="30" x2="${female ? 140 : 142}" y2="36" stroke="${female ? C.gold : '#8a6a3a'}" stroke-width="3" stroke-linecap="round"/>
    ${female ? `<circle cx="142" cy="36" r="4" fill="${C.cinnabar}"/>` : ''}
    <!-- 鬓发 -->
    <path d="M 74 92 q -6 30 2 54" stroke="${C.hair}" stroke-width="9" fill="none" stroke-linecap="round"/>
    <path d="M 166 92 q 6 30 -2 54" stroke="${C.hair}" stroke-width="9" fill="none" stroke-linecap="round"/>`;

  // —— 五官 ——
  const face = `
    <g stroke="${O}" stroke-linecap="round" fill="none">
      <path d="M 96 100 q 8 -5 17 -1" stroke-width="2"/>
      <path d="M 127 99 q 9 -4 17 1" stroke-width="2"/>
    </g>
    <g fill="${O}">
      <ellipse cx="105" cy="110" rx="4.6" ry="5.4"/>
      <ellipse cx="135" cy="110" rx="4.6" ry="5.4"/>
    </g>
    <circle cx="106.6" cy="108" r="1.5" fill="#fff"/><circle cx="136.6" cy="108" r="1.5" fill="#fff"/>
    <path d="M 116 116 q 4 4 8 0" stroke="${C.skinSh}" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    <path d="M 113 126 q 7 5 14 0" stroke="${C.cinnabar}" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.8"/>
    <ellipse cx="96" cy="120" rx="6" ry="4" fill="${C.cinnabar}" opacity="0.16"/>
    <ellipse cx="144" cy="120" rx="6" ry="4" fill="${C.cinnabar}" opacity="0.16"/>
    ${female ? `<path d="M 120 78 q -4 6 0 10 q 4 -4 0 -10 Z" fill="${C.cinnabar}"/>` : ''}`;

  const body = `${ground}${feet}${ribbon}${backHair}${robeBody}${sleeves}${collar}${belt}${farHand}${frontLocks}${sword}${head}${hairTop}${face}`;
  return `<g transform="translate(${x} ${y}) scale(${scale})">${body}</g>`;
}

/* ============================== 合成场景 ============================== */

// 1) 纯水墨山水（游戏世界背景）
function sceneLandscape(w = 800, h = 1100) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  ${DEFS}
  ${paper(w, h)}
  ${birds(140, 150, 5, 1.1)}
  <!-- 远山入雾 -->
  ${ridge([[-20, 430], [120, 360], [260, 420], [430, 330], [600, 410], [820, 360]], 'url(#mtnFar)', { op: 0.8, bottom: 1100 })}
  ${mistBand(380, 470, 520, 70, 0.9, true)}
  <!-- 中景群峰 -->
  ${ridge([[-20, 620], [110, 470], [240, 560], [360, 470], [520, 590], [700, 500], [820, 580]], 'url(#mtnMid)', { bottom: 1100 })}
  ${mistBand(250, 660, 360, 54, 0.85)}
  ${mistBand(620, 690, 320, 50, 0.8)}
  <!-- 近峰主山 -->
  ${ridge([[-20, 900], [80, 690], [180, 820], [300, 720], [430, 880], [560, 900]], 'url(#mtnNear)', { bottom: 1100 })}
  <!-- 留白江水（蜿蜒） -->
  <path d="M 60 1060 C 200 1010 240 980 420 980 C 600 980 660 940 800 936 L 800 1100 L 60 1100 Z"
        fill="${C.paperHi}" opacity="0.9" filter="url(#wetSoft)"/>
  <path d="M 120 1030 C 280 1000 360 992 520 996" stroke="${C.ink3}" stroke-width="2" fill="none" opacity="0.4"/>
  <path d="M 180 1058 C 340 1034 460 1030 620 1040" stroke="${C.ink3}" stroke-width="1.5" fill="none" opacity="0.3"/>
  <!-- 近景松 + 石 -->
  ${pine(660, 1010, 1.15)}
  <path d="M 70 1010 q 40 -30 96 -12 q 20 8 6 24 q -60 18 -110 6 Z" fill="${C.ink2}" opacity="0.85" filter="url(#wet)"/>
  <!-- 江上孤舟 -->
  <g opacity="0.9"><path d="M 360 1006 q 26 10 52 0 q -8 12 -26 12 q -18 0 -26 -12 Z" fill="${C.ink}" filter="url(#wetSoft)"/>
   <path d="M 386 1006 l 0 -22" stroke="${C.ink}" stroke-width="2"/><path d="M 386 986 q 14 4 14 14 l -14 0 Z" fill="${C.ink2}"/></g>
  ${seal(w - 96, h - 110, 60, '墨')}
  <text x="${w - 150}" y="${h - 60}" font-family="${FONTS.thin}" font-size="26" fill="${C.ink2}" text-anchor="end">壑外青山</text>
  </svg>`;
}

// 2) 角色设定（男女并立）
function sceneCharSheet(w = 900, h = 1000) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  ${DEFS}
  ${paper(w, h)}
  ${mistBand(450, 760, 520, 70, 0.7, true)}
  <ellipse cx="270" cy="520" rx="240" ry="280" fill="url(#halo)"/>
  <ellipse cx="640" cy="520" rx="240" ry="280" fill="url(#halo)"/>
  <text x="${w / 2}" y="90" font-family="${FONTS.flow}" font-size="64" fill="${C.ink}" text-anchor="middle">墨修 · 角色设定</text>
  <line x1="${w / 2}" y1="120" x2="${w / 2}" y2="900" stroke="${C.ink3}" stroke-width="1" stroke-dasharray="2 8" opacity="0.5"/>
  ${cultivator({ x: 150, y: 300, scale: 1.55, gender: 'female' })}
  ${cultivator({ x: 520, y: 300, scale: 1.55, gender: 'male' })}
  <text x="270" y="930" font-family="${FONTS.brush}" font-size="40" fill="${C.ink}" text-anchor="middle">坤 · 法修</text>
  <text x="640" y="930" font-family="${FONTS.brush}" font-size="40" fill="${C.ink}" text-anchor="middle">乾 · 剑修</text>
  <text x="270" y="962" font-family="${FONTS.thin}" font-size="22" fill="${C.ink2}" text-anchor="middle">白衣 · 朱钿 · 石青绦</text>
  <text x="640" y="962" font-family="${FONTS.thin}" font-size="22" fill="${C.ink2}" text-anchor="middle">玄发 · 高髻 · 朱砂绦</text>
  ${seal(w - 92, 40, 60, '稿')}
  </svg>`;
}

// 3) 开始/创角界面（仿参考图 1-2）
function sceneStart(w = 750, h = 1624) {
  const paths = ['体', '道', '法', '妖', '气', '禅'];
  const cols = [C.ink2, C.indigo, C.cinnabar, '#6b4a6b', '#3f6b52', '#9a7b3a'];
  // 六道：横向下凹弧形排布（中间「法」高起、被选中），仿参考图
  let wheel = '';
  const cx = w / 2, baseY = 1205, spread = 298, arcH = 54, N = paths.length;
  paths.forEach((p, i) => {
    const t = (i - (N - 1) / 2) / ((N - 1) / 2);   // -1..1
    const main = p === '法';
    const px = cx + t * spread;
    const py = baseY - (1 - t * t) * arcH - (main ? 18 : 0);
    const r = main ? 50 : 37;
    wheel += `<g>
      <ellipse cx="${px.toFixed(0)}" cy="${(py + r + 8).toFixed(0)}" rx="${r * 0.8}" ry="6" fill="${C.ink}" opacity="0.14" filter="url(#wetSoft)"/>
      <circle cx="${px.toFixed(0)}" cy="${py.toFixed(0)}" r="${r + 3}" fill="${C.ink}" opacity="0.1"/>
      <circle cx="${px.toFixed(0)}" cy="${py.toFixed(0)}" r="${r}" fill="${C.paperHi}" stroke="${cols[i]}" stroke-width="${main ? 4 : 3}"/>
      ${main ? `<circle cx="${px.toFixed(0)}" cy="${py.toFixed(0)}" r="${r + 9}" fill="none" stroke="${C.gold}" stroke-width="2.5" opacity="0.95"/>
                <circle cx="${px.toFixed(0)}" cy="${py.toFixed(0)}" r="${r + 16}" fill="none" stroke="${C.gold}" stroke-width="1" opacity="0.5"/>` : ''}
      <text x="${px.toFixed(0)}" y="${(py + r * 0.36).toFixed(0)}" font-family="${FONTS.brush}" font-size="${main ? 56 : 42}" fill="${cols[i]}" text-anchor="middle">${p}</text>
    </g>`;
  });
  // 乾坤（性别）—— 两枚朱/青菱形
  const diamond = (dx, col, label, sel) => `
    <g transform="translate(${cx + dx} 1308) rotate(45)"><rect x="-29" y="-29" width="58" height="58" rx="9" fill="${sel ? col : C.paperHi}" stroke="${col}" stroke-width="3"/></g>
    <text x="${cx + dx}" y="1320" font-family="${FONTS.brush}" font-size="36" fill="${sel ? C.paperHi : col}" text-anchor="middle">${label}</text>`;
  const gender = diamond(-72, C.indigo, '乾', false) + diamond(72, C.cinnabar, '坤', true);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  ${DEFS}
  ${paper(w, h)}
  ${birds(120, 180, 5, 1)}
  ${ridge([[-20, 500], [140, 410], [300, 480], [480, 380], [680, 470], [780, 410]], 'url(#mtnFar)', { op: 0.7, bottom: 900 })}
  ${mistBand(360, 560, 460, 70, 0.9, true)}
  ${ridge([[-20, 760], [120, 600], [260, 700], [420, 600], [600, 720], [780, 650]], 'url(#mtnMid)', { op: 0.85, bottom: 900 })}
  ${mistBand(380, 820, 460, 60, 0.85, true)}
  <!-- 标题（竖排书法） -->
  <text x="560" y="320" font-family="${FONTS.flow}" font-size="190" fill="${C.ink}" text-anchor="middle" filter="url(#wetSoft)">墨</text>
  <text x="560" y="520" font-family="${FONTS.flow}" font-size="190" fill="${C.ink}" text-anchor="middle" filter="url(#wetSoft)">修</text>
  <text x="690" y="300" font-family="${FONTS.thin}" font-size="40" fill="${C.ink2}" writing-mode="tb">一笔入道</text>
  <text x="690" y="470" font-family="${FONTS.thin}" font-size="40" fill="${C.ink2}" writing-mode="tb">万象成仙</text>
  ${seal(150, 250, 70, '墨')}
  <!-- 角色立绘（居中、上移留出转盘空间） -->
  <ellipse cx="${cx}" cy="760" rx="215" ry="300" fill="url(#halo)"/>
  ${cultivator({ x: cx - 186, y: 500, scale: 1.55, gender: 'female' })}
  <!-- 六道 + 性别 -->
  ${wheel}
  ${gender}
  <!-- 开始按钮 -->
  <g>
    <rect x="${cx - 175}" y="1380" width="350" height="86" rx="43" fill="${C.ink}" filter="url(#wetSoft)"/>
    <rect x="${cx - 169}" y="1386" width="338" height="74" rx="37" fill="none" stroke="${C.gold}" stroke-width="2" opacity="0.8"/>
    <text x="${cx}" y="1438" font-family="${FONTS.brush}" font-size="46" fill="${C.paperHi}" text-anchor="middle">开 始 修 炼</text>
  </g>
  <text x="${cx}" y="1520" font-family="${FONTS.thin}" font-size="26" fill="${C.ink2}" text-anchor="middle">解锁天赋后 · 可自由切换职业与性别</text>
  </svg>`;
}

/* ============================== 主程序 ============================== */
// 调试用：单角色大图
function sceneSolo() {
  const w = 760, h = 620;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${DEFS}
    ${paper(w, h)}
    ${cultivator({ x: 40, y: 40, scale: 1.6, gender: 'female' })}
    ${cultivator({ x: 400, y: 40, scale: 1.6, gender: 'male' })}</svg>`;
}
const jobs = {
  solo:  () => render(sceneSolo(), join(OUT, 'solo.png'), { width: 760 }),
  scene: () => render(sceneLandscape(), join(OUT, 'scene.png'), { width: 800 }),
  char:  () => render(sceneCharSheet(), join(OUT, 'character.png'), { width: 900 }),
  start: () => render(sceneStart(), join(OUT, 'start-screen.png'), { width: 750 }),
};
const which = process.argv[2] || 'all';
for (const [k, fn] of Object.entries(jobs)) {
  if (which === 'all' || which === k) console.log(k, fn());
}
