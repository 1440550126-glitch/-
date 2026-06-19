// 《墨修》角色：Q版水墨修士（赛璐璐分层上色 + 水润大眼 + 飘逸衣袖）
// 局部坐标 0..240(宽) × 0..360(高)，头中心约(120,96)，脚底约 y=324。
// 自带局部 <defs>（id 以 uid 区分），可在同一画布并排多个实例。

const P = {
  paper:'#efe7d6', ink:'#222a30', ink2:'#414b52', line:'#2b333a',
  skinHi:'#fdecd6', skin:'#f6dcbe', skinSh:'#e7bd92', skinLine:'#b9805a',
  robeHi:'#fbf6ec', robe:'#efe7d7', robeSh:'#d9cbb0', robeDeep:'#c3b290',
  hair:'#1d232c', hairSh:'#0f141b', hairHi:'#4a5d72',
  gold:'#caa15a', goldHi:'#ecd49a', white:'#ffffff',
  blade:'#e8edec', glowB:'#bfe6ff',
};

// 配色随性别/职业
function palette(female){
  return female
    ? { accent:'#3f6f70', accentHi:'#5fa0a0', accentDeep:'#284b4c', iris:'#5a8f8c', irisDeep:'#21403f' } // 法修·黛青
    : { accent:'#9c3a2c', accentHi:'#c45a44', accentDeep:'#6e2418', iris:'#7a4a2a', irisDeep:'#341d10' }; // 剑修·朱
}

export function cultivator({ x=0, y=0, scale=1, gender='female', uid, withGround=true, withGlow=true }={}){
  const female = gender==='female';
  const C = palette(female);
  const u = uid || gender;
  const id = s => `${s}_${u}`;

  /* —— 局部渐变 / 滤镜 —— */
  const defs = `<defs>
    <radialGradient id="${id('sk')}" cx="0.42" cy="0.32" r="0.75">
      <stop offset="0" stop-color="${P.skinHi}"/><stop offset="0.7" stop-color="${P.skin}"/><stop offset="1" stop-color="${P.skinSh}"/>
    </radialGradient>
    <linearGradient id="${id('robe')}" x1="0.2" y1="0" x2="0.8" y2="1">
      <stop offset="0" stop-color="${P.robeHi}"/><stop offset="0.55" stop-color="${P.robe}"/><stop offset="1" stop-color="${P.robeSh}"/>
    </linearGradient>
    <linearGradient id="${id('hair')}" x1="0.3" y1="0" x2="0.6" y2="1">
      <stop offset="0" stop-color="${P.hair}"/><stop offset="1" stop-color="${P.hairSh}"/>
    </linearGradient>
    <radialGradient id="${id('iris')}" cx="0.5" cy="0.32" r="0.7">
      <stop offset="0" stop-color="${C.iris}"/><stop offset="0.6" stop-color="${C.irisDeep}"/><stop offset="1" stop-color="#0d0a08"/>
    </radialGradient>
    <linearGradient id="${id('sash')}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${C.accentHi}"/><stop offset="1" stop-color="${C.accentDeep}"/>
    </linearGradient>
    <linearGradient id="${id('blade')}" x1="0" y1="0" x2="1" y2="0.1">
      <stop offset="0" stop-color="#fff"/><stop offset="0.5" stop-color="${P.blade}"/><stop offset="1" stop-color="#aab8bd"/>
    </linearGradient>
    <radialGradient id="${id('glow')}" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#fff7e8" stop-opacity="0.95"/>
      <stop offset="0.5" stop-color="${C.accentHi}" stop-opacity="0.18"/>
      <stop offset="1" stop-color="#fff7e8" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="${id('orb')}" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#fffdf6"/><stop offset="0.5" stop-color="${C.accentHi}" stop-opacity="0.7"/><stop offset="1" stop-color="${C.accentHi}" stop-opacity="0"/>
    </radialGradient>
    <filter id="${id('soft')}" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3"/></filter>
    <filter id="${id('soft1')}" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="1.1"/></filter>
    <clipPath id="${id('eL')}"><path d="M 92 112 C 92 100 116 100 116 112 C 116 123 92 123 92 112 Z"/></clipPath>
    <clipPath id="${id('eR')}"><path d="M 124 112 C 124 100 148 100 148 112 C 148 123 124 123 124 112 Z"/></clipPath>
  </defs>`;

  /* —— 氛围：柔光 + 灵气浮光 —— */
  const glow = withGlow ? `<ellipse cx="120" cy="150" rx="150" ry="180" fill="url(#${id('glow')})" filter="url(#${id('soft')})"/>` : '';
  const orbs = withGlow ? `
    <circle cx="42" cy="128" r="6" fill="url(#${id('orb')})" opacity="0.8"/>
    <circle cx="202" cy="104" r="7" fill="url(#${id('orb')})" opacity="0.8"/>` : '';

  /* —— 落地投影 —— */
  const ground = withGround
    ? `<ellipse cx="120" cy="330" rx="84" ry="15" fill="${P.ink}" opacity="0.18" filter="url(#${id('soft')})"/>` : '';

  /* —— 飘带（身后） —— */
  const ribbon = `<path d="M 150 178 q 70 26 58 100 q -6 36 18 64 q -36 -6 -44 -50 q -8 -48 -44 -94 Z"
      fill="${C.accent}" opacity="0.22" filter="url(#${id('soft1')})"/>`;

  /* —— 后发 —— */
  const backHair = `<path d="M 78 70 C 50 96 50 150 64 210 C 70 240 86 262 104 274
      C 92 250 86 210 88 150 C 56 150 60 96 92 72 Z"
      fill="${P.hairSh}"/>
    <path d="M 162 70 C 190 96 190 150 176 210 C 170 240 154 262 136 274
      C 148 250 154 210 152 150 C 184 150 180 96 148 72 Z"
      fill="${P.hairSh}"/>`;

  /* —— 云头履 —— */
  const feet = `<path d="M 98 312 q -14 2 -18 12 q 0 8 10 8 l 18 0 0 -20 Z" fill="${P.ink2}" stroke="${P.line}" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M 142 312 q 14 2 18 12 q 0 8 -10 8 l -18 0 0 -20 Z" fill="${P.ink2}" stroke="${P.line}" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M 86 326 q 14 5 30 0 M 124 326 q 16 5 30 0" stroke="${P.goldHi}" stroke-width="1.6" fill="none" opacity="0.8"/>`;

  /* —— 远袖（迎风外扬） —— */
  const farSleeve = `<path d="M 150 168 C 184 168 210 196 214 230 C 216 248 206 258 190 252
      C 184 230 168 200 146 184 Z" fill="url(#${id('robe')})" stroke="${P.line}" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M 190 248 C 184 226 170 202 150 188" stroke="${P.robeDeep}" stroke-width="1.6" fill="none" opacity="0.7"/>`;

  /* —— 袍主体（A字，分层下摆） —— */
  const robe = `
    <path d="M 92 166 C 80 184 78 204 86 220
             C 70 256 58 292 56 314 Q 90 326 120 326 Q 150 326 184 314
             C 182 292 170 256 154 220 C 162 204 160 184 148 166 Q 120 158 92 166 Z"
          fill="url(#${id('robe')})" stroke="${P.line}" stroke-width="2.6" stroke-linejoin="round"/>
    <!-- 暗面（右下） -->
    <path d="M 120 200 C 140 230 150 270 150 314 Q 168 312 184 314 C 182 292 170 256 154 220 C 160 206 160 190 150 170 Z"
          fill="${P.robeSh}" opacity="0.55"/>
    <!-- 内袍（下摆露出一层） -->
    <path d="M 70 300 Q 120 318 170 300 L 168 312 Q 120 330 72 312 Z" fill="${P.robeDeep}" opacity="0.85"/>
    <path d="M 70 300 Q 120 318 170 300" stroke="${C.accent}" stroke-width="2.2" fill="none" opacity="0.85"/>
    <!-- 衣纹 -->
    <path d="M 104 182 q -10 60 -12 126" stroke="${P.robeDeep}" stroke-width="1.5" fill="none" opacity="0.6"/>
    <path d="M 138 184 q 8 56 8 120" stroke="${P.robeDeep}" stroke-width="1.5" fill="none" opacity="0.5"/>
    <path d="M 120 196 l -2 116" stroke="${P.robeDeep}" stroke-width="1.4" fill="none" opacity="0.45"/>`;

  /* —— 交领右衽 + 内衬 —— */
  const collar = `
    <path d="M 96 166 Q 120 196 120 196 Q 120 196 144 166 L 150 172
             Q 120 206 120 206 Q 120 206 90 172 Z" fill="${P.robeHi}" stroke="${P.line}" stroke-width="2.2" stroke-linejoin="round"/>
    <path d="M 100 170 Q 120 198 120 198 L 116 206 Q 96 178 96 178 Z" fill="${C.accent}" opacity="0.9"/>
    <path d="M 140 170 Q 120 198 120 198 L 124 206 Q 144 178 144 178 Z" fill="${C.accentDeep}" opacity="0.55"/>`;

  /* —— 腰带 + 结 + 流苏 + 玉佩 —— */
  const sash = `
    <path d="M 80 224 Q 120 240 160 224 L 158 250 Q 120 266 82 250 Z" fill="url(#${id('sash')})" stroke="${P.line}" stroke-width="1.8"/>
    <path d="M 108 236 q 12 8 24 0 q 4 12 -4 18 q -8 4 -16 0 q -8 -6 -4 -18 Z" fill="${C.accentHi}" stroke="${P.line}" stroke-width="1.4"/>
    <path d="M 112 254 q -8 34 -4 60 M 128 254 q 8 32 4 58" stroke="url(#${id('sash')})" stroke-width="6" fill="none" stroke-linecap="round"/>
    <circle cx="120" cy="252" r="5" fill="${P.gold}" stroke="${P.line}" stroke-width="1"/>
    <ellipse cx="120" cy="270" rx="6" ry="9" fill="#bfe3d6" stroke="${P.gold}" stroke-width="1.4"/>
    <path d="M 120 280 q -4 14 -2 26" stroke="${C.accentHi}" stroke-width="3" fill="none" stroke-linecap="round"/>`;

  /* —— 剑（近手持，剑尖朝上，剑刃发光） —— */
  const sword = `
    <g>
      <path d="M 96 232 L 70 86 q 0 -8 4 -8 q 4 0 5 8 L 100 230 Z" fill="${P.glowB}" opacity="0.5" filter="url(#${id('soft1')})"/>
      <path d="M 97 230 L 73 86 L 67 88 L 91 232 Z" fill="url(#${id('blade')})" stroke="#9fb0b4" stroke-width="0.8"/>
      <line x1="80" y1="92" x2="95" y2="226" stroke="#fff" stroke-width="1.4" opacity="0.8"/>
      <path d="M 85 230 l 22 7 -3 9 -22 -7 Z" fill="${P.gold}" stroke="${P.line}" stroke-width="1.4"/>
      <rect x="90" y="236" width="13" height="26" rx="5" transform="rotate(9 96 249)" fill="${P.ink2}" stroke="${P.line}" stroke-width="1.4"/>
      <path d="M 96 240 l 0 18 M 92 240 l 1 17 M 100 241 l -1 16" stroke="${P.goldHi}" stroke-width="0.9" opacity="0.7"/>
      <ellipse cx="100" cy="248" rx="11" ry="9" fill="url(#${id('sk')})" stroke="${P.skinLine}" stroke-width="1.6"/>
      <path d="M 95 244 q 8 -2 12 2" stroke="${P.skinLine}" stroke-width="1.2" fill="none" opacity="0.7"/>
      <circle cx="98" cy="236" r="3.2" fill="${C.accentHi}"/>
      <path d="M 98 238 q -14 16 -10 42 M 98 238 q -2 22 -12 40" stroke="${C.accentHi}" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M 80 276 q 6 12 0 24 M 86 278 q 5 11 -1 22" stroke="${C.accent}" stroke-width="5.5" fill="none" stroke-linecap="round"/>
    </g>`;

  /* —— 颈 —— */
  const neck = `<path d="M 108 138 q 12 12 24 0 l 0 18 q -12 8 -24 0 Z" fill="${P.skin}" stroke="${P.skinLine}" stroke-width="1.4"/>
    <path d="M 108 150 q 12 8 24 0" stroke="${P.skinSh}" stroke-width="2" fill="none" opacity="0.6"/>`;

  /* —— 头（含下颌） —— */
  const head = `<path d="M 74 96 C 74 58 94 50 120 50 C 146 50 166 58 166 96
      C 166 124 150 140 120 142 C 90 140 74 124 74 96 Z" fill="url(#${id('sk')})" stroke="${P.skinLine}" stroke-width="2"/>
    <ellipse cx="74" cy="104" rx="6" ry="9" fill="${P.skin}" stroke="${P.skinLine}" stroke-width="1.4"/>
    <ellipse cx="166" cy="104" rx="6" ry="9" fill="${P.skin}" stroke="${P.skinLine}" stroke-width="1.4"/>`;

  /* —— 一只眼 —— */
  const eye = (ex, side) => {
    const clip = side === 'L' ? id('eL') : id('eR');
    const white = `M ${ex-12} 112 C ${ex-12} 100 ${ex+12} 100 ${ex+12} 112 C ${ex+12} 123 ${ex-12} 123 ${ex-12} 112 Z`;
    const flick = side === 'L' ? `M ${ex-11} 109 q -5 -2 -8 -6` : `M ${ex+11} 109 q 5 -2 8 -6`;
    return `
      <path d="${white}" fill="#fffdf8"/>
      <g clip-path="url(#${clip})">
        <circle cx="${ex}" cy="114.5" r="10.5" fill="url(#${id('iris')})"/>
        <circle cx="${ex}" cy="116" r="5" fill="#0c0908"/>
        <path d="M ${ex-7} 119 q 7 7 14 0" stroke="${C.iris}" stroke-width="3" fill="none" opacity="0.85"/>
        <circle cx="${ex-4}" cy="109.5" r="3.7" fill="#fff"/>
        <circle cx="${ex+4}" cy="118" r="1.8" fill="#fff" opacity="0.9"/>
      </g>
      <path d="M ${ex-12} 112 C ${ex-11} 99 ${ex+11} 99 ${ex+12} 112" stroke="${P.line}" stroke-width="3.6" fill="none" stroke-linecap="round"/>
      <path d="${flick}" stroke="${P.line}" stroke-width="2.2" fill="none" stroke-linecap="round"/>
      <path d="M ${ex-9} 121 q 9 3 18 0" stroke="${P.skinLine}" stroke-width="1.4" fill="none" stroke-linecap="round" opacity="0.55"/>
      <path d="M ${ex-11} 94 Q ${ex} 89 ${ex+11} 95" stroke="${P.hairSh}" stroke-width="2.8" fill="none" stroke-linecap="round"/>`;
  };

  /* —— 五官 —— */
  const face = `
    ${eye(104,'L')}${eye(136,'R')}
    <path d="M 117 124 q 3 4 6 1" stroke="${P.skinLine}" stroke-width="1.4" fill="none" stroke-linecap="round" opacity="0.7"/>
    <path d="M 113 132 q 7 6 14 0" stroke="${C.accentDeep}" stroke-width="2.4" fill="none" stroke-linecap="round"/>
    <path d="M 115 133 q 5 3 10 0" stroke="#d98a6e" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.6"/>
    <ellipse cx="93" cy="124" rx="7" ry="4.5" fill="#e8896f" opacity="0.28" filter="url(#${id('soft1')})"/>
    <ellipse cx="147" cy="124" rx="7" ry="4.5" fill="#e8896f" opacity="0.28" filter="url(#${id('soft1')})"/>
    ${female ? `<path d="M 120 84 q -5 5 0 11 q 5 -6 0 -11 Z" fill="#b1402f"/>
       <circle cx="120" cy="80" r="2.2" fill="#b1402f"/>` : ''}`;

  /* —— 前发 / 刘海 / 高光 / 发簪 —— */
  const hairFront = `
    <path d="M 70 98 C 64 52 98 36 120 36 C 142 36 176 54 170 98 C 150 80 90 80 70 98 Z" fill="url(#${id('hair')})"/>
    <!-- 天使环高光 -->
    <path d="M 86 66 C 98 57 110 54 122 54 C 134 54 146 59 154 71" stroke="${P.hairHi}" stroke-width="5" fill="none" stroke-linecap="round" opacity="0.5" filter="url(#${id('soft1')})"/>
    <!-- 侧鬓 -->
    <path d="M 74 90 q -7 28 1 52" stroke="${P.hair}" stroke-width="12" fill="none" stroke-linecap="round"/>
    <path d="M 166 90 q 7 28 -1 52" stroke="${P.hair}" stroke-width="12" fill="none" stroke-linecap="round"/>
    <!-- 刘海·中分两束（圆头软笔触） -->
    <path d="M 102 78 q -8 14 -16 26" stroke="url(#${id('hair')})" stroke-width="15" fill="none" stroke-linecap="round"/>
    <path d="M 138 78 q 8 14 16 26" stroke="url(#${id('hair')})" stroke-width="15" fill="none" stroke-linecap="round"/>
    <path d="M 120 76 q -2 8 -2 14" stroke="url(#${id('hair')})" stroke-width="10" fill="none" stroke-linecap="round"/>
    <!-- 发髻 + 簪 -->
    <ellipse cx="120" cy="40" rx="22" ry="16" fill="url(#${id('hair')})" stroke="${P.hairSh}" stroke-width="1.2"/>
    <ellipse cx="114" cy="36" rx="9" ry="6" fill="${P.hairHi}" opacity="0.5"/>
    <line x1="102" y1="36" x2="140" y2="42" stroke="${P.gold}" stroke-width="3.4" stroke-linecap="round"/>
    <circle cx="140" cy="42" r="4" fill="${P.goldHi}" stroke="${P.gold}" stroke-width="1"/>
    ${female ? `<path d="M 140 45 q 0 12 0 18" stroke="${P.gold}" stroke-width="1.4"/><circle cx="140" cy="66" r="3.4" fill="#b1402f"/>` : ''}`;

  /* —— 前垂发（女） —— */
  const frontLocks = female ? `
    <path d="M 86 110 C 78 160 80 210 92 246 C 96 258 92 266 86 268 C 82 250 74 210 74 160 C 74 138 78 120 86 110 Z"
          fill="url(#${id('hair')})"/>
    <path d="M 154 110 C 162 160 160 210 148 246 C 144 258 148 266 154 268 C 158 250 166 210 166 160 C 166 138 162 120 154 110 Z"
          fill="url(#${id('hair')})"/>
    <path d="M 84 130 q -4 50 4 100" stroke="${P.hairHi}" stroke-width="2" fill="none" opacity="0.4"/>
    <path d="M 156 130 q 4 50 -4 100" stroke="${P.hairHi}" stroke-width="2" fill="none" opacity="0.4"/>` : '';

  const body = `${defs}${glow}${orbs}${ground}${ribbon}${backHair}${feet}${farSleeve}${robe}${collar}${sash}`
    + `${frontLocks}${sword}${neck}${head}${face}${hairFront}`;
  return `<g transform="translate(${x} ${y}) scale(${scale})">${body}</g>`;
}
