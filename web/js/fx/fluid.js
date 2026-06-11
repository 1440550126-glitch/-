// 3D 感流体背景：WebGL fbm 噪声星云光雾（低分辨率渲染 + 上采样，省电）
// 不支持 WebGL 时回退为 CSS 渐变呼吸。
const FRAG = `
precision mediump float;
uniform vec2 u_res;
uniform float u_t;
uniform float u_dark;

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
void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 p = uv * vec2(u_res.x/u_res.y, 1.0) * 1.6;
  float t = u_t * 0.045;
  // 双层流动域扭曲 → 缓慢流体感
  vec2 q = vec2(fbm(p + t), fbm(p + vec2(5.2,1.3) - t*0.7));
  vec2 r = vec2(fbm(p + 2.6*q + vec2(1.7,9.2) + t*0.6), fbm(p + 2.2*q + vec2(8.3,2.8) - t*0.4));
  float f = fbm(p + 2.4*r);

  vec3 cA = mix(vec3(0.965,0.945,0.995), vec3(0.10,0.09,0.16), u_dark);
  vec3 cB = mix(vec3(0.988,0.930,0.965), vec3(0.16,0.12,0.25), u_dark);
  vec3 cC = mix(vec3(0.760,0.700,0.990), vec3(0.42,0.30,0.85), u_dark);
  vec3 cD = mix(vec3(0.995,0.760,0.870), vec3(0.85,0.35,0.60), u_dark);

  vec3 col = mix(cA, cB, smoothstep(0.0,1.0,uv.y));
  col = mix(col, cC, smoothstep(0.35,0.95,f) * (0.34 + 0.1*sin(t*2.0)));
  col = mix(col, cD, smoothstep(0.55,1.0,length(q)) * 0.22);
  // 微微的光斑
  col += (0.5 + 0.5*sin(t*3.0)) * 0.045 * smoothstep(0.75, 1.0, f);
  gl_FragColor = vec4(col, 1.0);
}`;

export function initFluid(canvas, { dark = 0 } = {}) {
  const gl = canvas.getContext('webgl', { antialias: false, depth: false, alpha: false });
  if (!gl) {
    canvas.style.background = 'linear-gradient(160deg,#f6f2fd,#fdeef6,#eef4ff)';
    canvas.style.backgroundSize = '300% 300%';
    canvas.style.animation = 'shimmer 14s ease-in-out infinite';
    return { setDark() {}, destroy() {} };
  }
  const vs = gl.createShader(gl.VERTEX_SHADER);
  gl.shaderSource(vs, 'attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}');
  gl.compileShader(vs);
  const fsh = gl.createShader(gl.FRAGMENT_SHADER);
  gl.shaderSource(fsh, FRAG);
  gl.compileShader(fsh);
  if (!gl.getShaderParameter(fsh, gl.COMPILE_STATUS)) {
    console.warn('fluid shader:', gl.getShaderInfoLog(fsh));
    return { setDark() {}, destroy() {} };
  }
  const prog = gl.createProgram();
  gl.attachShader(prog, vs); gl.attachShader(prog, fsh); gl.linkProgram(prog);
  gl.useProgram(prog);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, 'a');
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const uRes = gl.getUniformLocation(prog, 'u_res');
  const uT = gl.getUniformLocation(prog, 'u_t');
  const uDark = gl.getUniformLocation(prog, 'u_dark');

  let darkV = dark, raf = 0, running = true;
  const SCALE = 0.28;     // 低分辨率渲染省电
  function resize() {
    canvas.width = Math.max(2, Math.floor(innerWidth * SCALE));
    canvas.height = Math.max(2, Math.floor(innerHeight * SCALE));
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  resize();
  addEventListener('resize', resize);
  const t0 = performance.now();
  let last = 0;
  function frame(ts) {
    raf = requestAnimationFrame(frame);
    if (!running || ts - last < 50) return;   // ~20fps 足够流体感且省电
    last = ts;
    gl.uniform2f(uRes, canvas.width, canvas.height);
    gl.uniform1f(uT, (ts - t0) / 1000);
    gl.uniform1f(uDark, darkV);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  raf = requestAnimationFrame(frame);
  document.addEventListener('visibilitychange', () => { running = !document.hidden; });
  return {
    setDark(v) { darkV = v; },
    destroy() { cancelAnimationFrame(raf); }
  };
}
