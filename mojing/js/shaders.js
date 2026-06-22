// 魔镜魔镜 · WebGL 着色器（GLSL ES 1.00 / WebGL1，兼容性最佳）
// 全部美颜/瘦身/调色在 GPU 片元着色器里实时完成，不上传任何画面。

// 共用顶点着色器：全屏三角形，输出 0..1 的 uv
export const VERT = `
attribute vec2 a_pos;
varying vec2 v_uv;
void main(){
  v_uv = a_pos * 0.5 + 0.5;
  gl_Position = vec4(a_pos, 0.0, 1.0);
}`;

// 可分离高斯模糊（横/竖各跑一遍）——磨皮的"低频底"
// 5 次采样近似 9 抽头高斯（利用线性采样权重）
export const BLUR_FRAG = `
precision mediump float;
uniform sampler2D u_tex;
uniform vec2 u_texel;   // (1/宽, 1/高)
uniform vec2 u_dir;     // (1,0) 横向 或 (0,1) 纵向
uniform float u_radius; // 模糊半径（像素）
varying vec2 v_uv;
void main(){
  vec2 d = u_texel * u_dir * u_radius;
  vec4 c = texture2D(u_tex, v_uv) * 0.227027;
  c += texture2D(u_tex, v_uv + d * 1.3846) * 0.316216;
  c += texture2D(u_tex, v_uv - d * 1.3846) * 0.316216;
  c += texture2D(u_tex, v_uv + d * 3.2308) * 0.070270;
  c += texture2D(u_tex, v_uv - d * 3.2308) * 0.070270;
  gl_FragColor = c;
}`;

// 主合成着色器：瘦身形变 → 频率分离磨皮 → 美白/红润/色温 → 明暗对比/饱和 → 滤镜 → 暗角
export const MAIN_FRAG = `
precision mediump float;
uniform sampler2D u_sharp;   // 原始视频帧（清晰）
uniform sampler2D u_blur;    // 模糊帧（低频）
uniform float u_mirror;      // 前置自拍镜像

uniform float u_smooth;      // 磨皮 0..1
uniform float u_whiten;      // 美白 0..1
uniform float u_rosy;        // 红润 0..1
uniform float u_sharpen;     // 锐化/清晰度 0..1
uniform float u_bright;      // 亮度 -1..1
uniform float u_contrast;    // 对比度 -1..1
uniform float u_sat;         // 饱和度 -1..1
uniform float u_temp;        // 色温 -1..1（+暖 -冷）
uniform float u_vignette;    // 暗角 0..1

uniform float u_slimFace;    // 瘦脸 0..1
uniform float u_slimBody;    // 瘦身 0..1
uniform float u_faceOn;      // 是否检测到人脸
uniform vec2  u_faceC;       // 人脸中心 uv
uniform vec2  u_faceR;       // 人脸半径 uv

uniform float u_filter;      // 滤镜编号
uniform float u_fstr;        // 滤镜强度 0..1
uniform float u_compare;     // 长按看原图 → 1 时直出

varying vec2 v_uv;

float luma(vec3 c){ return dot(c, vec3(0.299, 0.587, 0.114)); }

// 液化瘦身：朝中轴/人脸中心做横向收缩（逆映射时向外取样 → 主体变窄）
vec2 slim(vec2 uv){
  // 瘦脸：以人脸框为带，集中在脸部高度（用平方代替 pow，避免负底数未定义）
  vec2 fc = u_faceOn > 0.5 ? u_faceC : vec2(0.5, 0.62);
  vec2 fr = u_faceOn > 0.5 ? u_faceR : vec2(0.22, 0.26);
  float ay = (uv.y - fc.y) / max(fr.y * 1.15, 0.05);
  float faceBand = exp(-ay * ay);
  float dxf = uv.x - fc.x;
  float axf = dxf / max(fr.x * 1.35, 0.06);
  float xfallF = exp(-axf * axf);
  float pushF = u_slimFace * 0.45 * faceBand * xfallF;
  uv.x = fc.x + dxf * (1.0 + pushF);

  // 瘦身：以画面中轴为带，覆盖躯干（画面中下部）
  float bodyBand = smoothstep(0.04, 0.30, uv.y) * (1.0 - smoothstep(0.62, 0.92, uv.y));
  float dxb = uv.x - 0.5;
  float axb = dxb / 0.34;
  float xfallB = exp(-axb * axb);
  float pushB = u_slimBody * 0.30 * bodyBand * xfallB;
  uv.x = 0.5 + dxb * (1.0 + pushB);
  return uv;
}

vec3 applyFilter(vec3 c, float f, float s){
  vec3 o = c;
  if (f < 0.5) {                       // 原图
    return c;
  } else if (f < 1.5) {                // 清新
    o = c * vec3(0.96, 1.05, 1.02);
    o = mix(vec3(luma(o)), o, 1.12) + 0.02;
  } else if (f < 2.5) {                // 日系
    o = c * vec3(1.03, 1.0, 0.96) + 0.045;
    o = (o - 0.5) * 0.9 + 0.5;
  } else if (f < 3.5) {                // 复古
    vec3 sep = vec3(dot(c, vec3(0.393, 0.769, 0.189)),
                    dot(c, vec3(0.349, 0.686, 0.168)),
                    dot(c, vec3(0.272, 0.534, 0.131)));
    o = mix(c, sep, 0.6) * 0.96 + 0.02;
  } else if (f < 4.5) {                // 黑白
    o = vec3((luma(c) - 0.5) * 1.12 + 0.5);
  } else if (f < 5.5) {                // 电影感（青橙）
    float L = luma(c);
    o = mix(c * vec3(0.92, 0.98, 1.07), c * vec3(1.09, 1.0, 0.9), smoothstep(0.28, 0.72, L));
    o = (o - 0.5) * 1.07 + 0.5;
  } else if (f < 6.5) {                // 冷白皮
    o = pow(max(c, 0.0), vec3(0.9)) + vec3(0.0, 0.012, 0.035);
    o = mix(vec3(luma(o)), o, 0.92);
  } else {                             // 暖阳
    o = c * vec3(1.06, 1.0, 0.91) + vec3(0.035, 0.012, 0.0);
  }
  return mix(c, o, s);
}

void main(){
  vec2 base = v_uv;
  if (u_mirror > 0.5) base.x = 1.0 - base.x;

  if (u_compare > 0.5) {               // 长按对比：直出原图
    gl_FragColor = vec4(texture2D(u_sharp, base).rgb, 1.0);
    return;
  }

  vec2 uv = slim(base);
  vec3 sharp = texture2D(u_sharp, uv).rgb;
  vec3 blur  = texture2D(u_blur,  uv).rgb;

  // —— 磨皮：频率分离（低频取模糊，高频按边缘/肤色受控保留）——
  float hp = luma(sharp) - luma(blur);                 // 高频细节
  float edge = smoothstep(0.05, 0.18, abs(hp));        // 边缘越强越不磨
  float skin = smoothstep(0.0, 0.22, sharp.r - sharp.b)
             * smoothstep(0.0, 0.18, sharp.g - sharp.b * 0.55);
  skin = clamp(skin, 0.0, 1.0);
  float sm = clamp(u_smooth * skin * (1.0 - edge), 0.0, 0.92);
  vec3 col = mix(sharp, blur, sm);
  col += hp * 0.25 * (1.0 - sm);                       // 回补一点质感，防止塑料脸

  // 锐化（清晰度）：非锐化掩模
  col += u_sharpen * (sharp - blur) * 1.6;

  // 美白：gamma 提亮 + 轻微抬白
  col = pow(max(col, 0.0), vec3(1.0 / (1.0 + u_whiten * 0.6)));
  col += u_whiten * 0.04;

  // 红润：仅作用于肤色区
  col += u_rosy * skin * vec3(0.10, 0.02, 0.03);

  // 色温
  col += u_temp * vec3(0.08, 0.015, -0.07);

  // 亮度 / 对比度
  col += u_bright * 0.25;
  col = (col - 0.5) * (1.0 + u_contrast * 0.7) + 0.5;

  // 饱和度
  col = mix(vec3(luma(col)), col, 1.0 + u_sat);

  // 滤镜
  col = applyFilter(col, u_filter, u_fstr);

  // 暗角（屏幕空间）
  float d = distance(base, vec2(0.5));
  col *= 1.0 - u_vignette * smoothstep(0.32, 0.85, d);

  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}`;
