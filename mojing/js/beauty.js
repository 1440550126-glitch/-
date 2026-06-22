// 魔镜魔镜 · 实时美颜引擎（WebGL1）
// 管线：视频帧 → 横向模糊(FBO) → 纵向模糊(FBO) → 合成(瘦身/磨皮/调色/滤镜) → 画布
import { VERT, BLUR_FRAG, MAIN_FRAG } from './shaders.js';

function compile(gl, type, src) {
  const sh = gl.createShader(type);
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    throw new Error('着色器编译失败：' + gl.getShaderInfoLog(sh));
  }
  return sh;
}

function program(gl, vsSrc, fsSrc) {
  const p = gl.createProgram();
  gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, vsSrc));
  gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, fsSrc));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
    throw new Error('着色器链接失败：' + gl.getProgramInfoLog(p));
  }
  return p;
}

function makeTarget(gl, w, h) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const fbo = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  return { tex, fbo, w, h };
}

export function createEngine(canvas) {
  const gl = canvas.getContext('webgl', {
    antialias: false, depth: false, alpha: false,
    preserveDrawingBuffer: true,   // 拍照/captureStream 抓帧需要
    premultipliedAlpha: false
  });
  if (!gl) throw new Error('当前环境不支持 WebGL，无法启动魔镜');

  const blurProg = program(gl, VERT, BLUR_FRAG);
  const mainProg = program(gl, VERT, MAIN_FRAG);

  // 全屏三角形
  const quad = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, quad);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);

  function bindQuad(prog) {
    const loc = gl.getAttribLocation(prog, 'a_pos');
    gl.bindBuffer(gl.ARRAY_BUFFER, quad);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  }

  // 视频纹理
  const videoTex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, videoTex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);

  let A = null, B = null, W = 0, H = 0;

  function resize(w, h) {
    if (w === W && h === H) return;
    W = w; H = h;
    canvas.width = w; canvas.height = h;
    if (A) { gl.deleteTexture(A.tex); gl.deleteFramebuffer(A.fbo); }
    if (B) { gl.deleteTexture(B.tex); gl.deleteFramebuffer(B.fbo); }
    A = makeTarget(gl, w, h);
    B = makeTarget(gl, w, h);
  }

  const U = {}; // uniform 位置缓存
  function u(prog, name) {
    const key = (prog === blurProg ? 'b:' : 'm:') + name;
    if (!(key in U)) U[key] = gl.getUniformLocation(prog, name);
    return U[key];
  }

  // 默认参数
  const face = { on: 0, cx: 0.5, cy: 0.62, rx: 0.22, ry: 0.26 };

  function setFace(f) {
    if (!f) { face.on = 0; return; }
    // 指数平滑，避免抖动
    face.on = 1;
    face.cx += (f.cx - face.cx) * 0.35;
    face.cy += (f.cy - face.cy) * 0.35;
    face.rx += (f.rx - face.rx) * 0.35;
    face.ry += (f.ry - face.ry) * 0.35;
  }
  function clearFace() { face.on = 0; }

  function blurPass(srcTex, dst, dirX, dirY, radius) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, dst.fbo);
    gl.viewport(0, 0, dst.w, dst.h);
    gl.useProgram(blurProg);
    bindQuad(blurProg);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, srcTex);
    gl.uniform1i(u(blurProg, 'u_tex'), 0);
    gl.uniform2f(u(blurProg, 'u_texel'), 1 / dst.w, 1 / dst.h);
    gl.uniform2f(u(blurProg, 'u_dir'), dirX, dirY);
    gl.uniform1f(u(blurProg, 'u_radius'), radius);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  // 渲染一帧。p = 参数对象，video = HTMLVideoElement，mirror = 是否镜像
  function render(video, p, mirror) {
    if (!video || video.readyState < 2) return;
    const vw = video.videoWidth, vh = video.videoHeight;
    if (!vw || !vh) return;
    resize(vw, vh);

    // 上传视频帧
    gl.bindTexture(gl.TEXTURE_2D, videoTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, video);

    // 磨皮所需的模糊底（半径随分辨率自适应）
    const radius = Math.max(1.5, H / 240);
    blurPass(videoTex, A, 1, 0, radius);   // 横
    blurPass(A.tex, B, 0, 1, radius);      // 竖 → B.tex 为最终模糊

    // 合成到画布
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, W, H);
    gl.useProgram(mainProg);
    bindQuad(mainProg);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, videoTex);
    gl.uniform1i(u(mainProg, 'u_sharp'), 0);
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, B.tex);
    gl.uniform1i(u(mainProg, 'u_blur'), 1);

    gl.uniform1f(u(mainProg, 'u_mirror'), mirror ? 1 : 0);
    gl.uniform1f(u(mainProg, 'u_smooth'), p.smooth);
    gl.uniform1f(u(mainProg, 'u_whiten'), p.whiten);
    gl.uniform1f(u(mainProg, 'u_rosy'), p.rosy);
    gl.uniform1f(u(mainProg, 'u_sharpen'), p.sharpen);
    gl.uniform1f(u(mainProg, 'u_bright'), p.brightness);
    gl.uniform1f(u(mainProg, 'u_contrast'), p.contrast);
    gl.uniform1f(u(mainProg, 'u_sat'), p.saturation);
    gl.uniform1f(u(mainProg, 'u_temp'), p.temperature);
    gl.uniform1f(u(mainProg, 'u_vignette'), p.vignette);
    gl.uniform1f(u(mainProg, 'u_slimFace'), p.slimFace);
    gl.uniform1f(u(mainProg, 'u_slimBody'), p.slimBody);
    gl.uniform1f(u(mainProg, 'u_filter'), p._filterId || 0);
    gl.uniform1f(u(mainProg, 'u_fstr'), p.filterStrength);
    gl.uniform1f(u(mainProg, 'u_compare'), p._compare ? 1 : 0);

    gl.uniform1f(u(mainProg, 'u_faceOn'), face.on);
    gl.uniform2f(u(mainProg, 'u_faceC'), face.cx, face.cy);
    gl.uniform2f(u(mainProg, 'u_faceR'), face.rx, face.ry);

    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  return {
    gl, canvas, render, setFace, clearFace,
    get size() { return { w: W, h: H }; }
  };
}
