// 青鸾 · 伪 3D 流体背景：fbm 高度场 + 法线光照（漫反射/高光）+ 鼠标扰动
// 低分辨率渲染上采样省电；标签页隐藏/滚出视口自动暂停；不支持 WebGL 时回退 CSS 渐变。
const FRAG = `
precision mediump float;
uniform vec2 u_res;
uniform float u_t;
uniform vec2 u_mouse;     // 0~1
uniform float u_boost;    // 鼠标活跃度 0~1

float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f*f*(3.0-2.0*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), u.x),
             mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), u.x), u.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for(int i=0;i<4;i++){ v += a*noise(p); p = p*2.03 + vec2(1.7,9.2); a *= 0.55; }
  return v;
}
// 流体高度场：双层域扭曲 + 鼠标隆起
float height(vec2 p, float t, vec2 m){
  vec2 q = vec2(fbm(p + t), fbm(p + vec2(5.2,1.3) - t*0.7));
  vec2 r = vec2(fbm(p + 2.4*q + vec2(1.7,9.2) + t*0.5), fbm(p + 2.1*q + vec2(8.3,2.8) - t*0.4));
  float h = fbm(p + 2.3*r);
  float d = length(p - m);
  h += (0.22 + 0.25*u_boost) * exp(-d*d*3.2);   // 鼠标处流体隆起
  return h;
}
void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  float aspect = u_res.x / u_res.y;
  vec2 p = uv * vec2(aspect, 1.0) * 1.55;
  vec2 m = u_mouse * vec2(aspect, 1.0) * 1.55;
  float t = u_t * 0.05;

  // 3D：以高度场近似曲面，差分求法线做光照
  float e = 0.045;
  float h  = height(p, t, m);
  float hx = height(p + vec2(e,0.0), t, m);
  float hy = height(p + vec2(0.0,e), t, m);
  vec3 n = normalize(vec3((h - hx)/e, (h - hy)/e, 1.35));
  vec3 lightDir = normalize(vec3(0.55, 0.65, 0.62));
  float diff = clamp(dot(n, lightDir), 0.0, 1.0);
  vec3 viewDir = vec3(0.0, 0.0, 1.0);
  float spec = pow(clamp(dot(reflect(-lightDir, n), viewDir), 0.0, 1.0), 26.0);

  // 青鸾配色：深墨青底 → 青碧 → 朱砂点染
  vec3 deep  = vec3(0.055, 0.135, 0.165);
  vec3 teal  = vec3(0.10, 0.45, 0.43);
  vec3 mint  = vec3(0.33, 0.76, 0.70);
  vec3 ember = vec3(0.89, 0.42, 0.30);

  vec3 col = mix(deep, teal, smoothstep(0.25, 0.85, h));
  col = mix(col, mint, smoothstep(0.62, 1.0, h) * 0.55);
  col = mix(col, ember, smoothstep(0.78, 1.05, h + 0.22*sin(t*2.0 + p.x*2.0)) * 0.16);
  col *= 0.66 + 0.5 * diff;                    // 漫反射体积感
  col += spec * vec3(0.55, 0.85, 0.80) * 0.5;  // 高光（流体表面反光）
  col += (0.5 + 0.5*sin(t*3.0)) * 0.03 * smoothstep(0.8, 1.0, h);
  // 顶部轻微暗角，让标题更清晰
  col *= 1.0 - 0.32 * smoothstep(0.55, 1.0, uv.y) * (1.0 - uv.x*0.25);
  gl_FragColor = vec4(col, 1.0);
}`;

export function initFluid(canvas, { scale = 0.3 } = {}) {
  const gl = canvas.getContext('webgl', { antialias: false, depth: false, alpha: false });
  if (!gl) {
    canvas.style.background = 'linear-gradient(135deg,#0e2a33,#0d3f41 55%,#15514c)';
    return { destroy() {} };
  }
  const compile = (type, src) => {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    return s;
  };
  const vs = compile(gl.VERTEX_SHADER, 'attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}');
  const fs = compile(gl.FRAGMENT_SHADER, FRAG);
  if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {
    console.warn('[fluid]', gl.getShaderInfoLog(fs));
    return { destroy() {} };
  }
  const prog = gl.createProgram();
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.linkProgram(prog);
  gl.useProgram(prog);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, 'a');
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const uRes = gl.getUniformLocation(prog, 'u_res');
  const uT = gl.getUniformLocation(prog, 'u_t');
  const uMouse = gl.getUniformLocation(prog, 'u_mouse');
  const uBoost = gl.getUniformLocation(prog, 'u_boost');

  let raf = 0;
  let visible = true;
  let alive = true;
  const mouse = { x: 0.72, y: 0.6, tx: 0.72, ty: 0.6, boost: 0 };

  function resize() {
    const r = canvas.getBoundingClientRect();
    canvas.width = Math.max(2, Math.floor(r.width * scale));
    canvas.height = Math.max(2, Math.floor(r.height * scale));
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  const onMove = (e) => {
    const r = canvas.getBoundingClientRect();
    mouse.tx = (e.clientX - r.left) / Math.max(1, r.width);
    mouse.ty = 1 - (e.clientY - r.top) / Math.max(1, r.height);
    mouse.boost = 1;
  };
  canvas.parentElement?.addEventListener('pointermove', onMove);

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const t0 = performance.now();
  function frame(now) {
    if (!alive) return;
    if (visible && !document.hidden) {
      mouse.x += (mouse.tx - mouse.x) * 0.06;          // 非线性追随（指数趋近）
      mouse.y += (mouse.ty - mouse.y) * 0.06;
      mouse.boost *= 0.975;
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uT, reduced ? 12 : (now - t0) / 1000);
      gl.uniform2f(uMouse, mouse.x, mouse.y);
      gl.uniform1f(uBoost, mouse.boost);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (reduced) { alive = false; return; }          // 减少动态：渲染一帧静态流体
    }
    raf = requestAnimationFrame(frame);
  }
  const io = new IntersectionObserver(([en]) => { visible = !!en?.isIntersecting; });
  io.observe(canvas);
  addEventListener('resize', resize);
  resize();
  raf = requestAnimationFrame(frame);

  return {
    destroy() {
      alive = false;
      cancelAnimationFrame(raf);
      io.disconnect();
      removeEventListener('resize', resize);
      canvas.parentElement?.removeEventListener('pointermove', onMove);
    }
  };
}
