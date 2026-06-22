// 魔镜魔镜 · 应用入口：相机 → 实时美颜 → 拍照/录像 → 保存分享
import { createEngine } from './beauty.js';
import { createCamera, createFaceTracker } from './camera.js';
import { createStore } from './store.js';
import { createUI } from './ui.js';
import { createGallery } from './gallery.js';
import { applyPreset, filterCode } from './presets.js';

const $ = (s) => document.querySelector(s);

const video = $('#cam');
const stage = $('#stage');
const store = createStore();
const gallery = createGallery();

let engine, camera, faceTracker;
let mirror = true;          // 前置默认镜像
let mode = 'photo';         // photo | video
let compare = false;        // 长按看原图
let recTimer = 0, recStart = 0;
let selVideoId = null, selAudioId = null;   // 当前选中的摄像头/麦克风

const ui = createUI(store, {
  applyPreset: (preset, intensity) => applyPreset(store, preset, intensity)
});

// —— 渲染循环 ——
function loop() {
  requestAnimationFrame(loop);
  if (!engine) return;
  const p = store.get();
  engine.render(video, {
    ...p,
    _filterId: filterCode(p.filter),
    _compare: compare
  }, mirror);
}

// —— 启动相机 ——
async function boot() {
  try {
    engine = createEngine(stage);
  } catch (e) {
    return fail('你的浏览器不支持 WebGL，无法运行魔镜 😢');
  }
  camera = createCamera(video);
  try {
    const info = await camera.start('user');
    mirror = info.isFront;
  } catch (e) {
    return fail(permissionMessage(e));
  }
  $('#boot').hidden = true;

  // 人脸检测（瘦脸自动对位）——支持则默认开启
  faceTracker = createFaceTracker(video, (f) => engine.setFace(f));
  if (faceTracker.supported) {
    faceTracker.start();
    $('#btn-face').hidden = false;
    $('#btn-face').classList.add('on');
  }
  await initDevices();
  loop();
}

function fail(msg) {
  const boot = $('#boot');
  boot.hidden = false;
  boot.innerHTML = `<div class="boot-card"><div class="boot-logo">🪞</div>
    <p class="boot-msg">${msg}</p>
    <button id="retry" class="boot-btn">重新授权</button></div>`;
  $('#retry')?.addEventListener('click', () => location.reload());
}

function permissionMessage(e) {
  if (e && (e.name === 'NotAllowedError' || e.name === 'SecurityError')) {
    return '需要相机权限才能照镜子～请在浏览器里允许摄像头';
  }
  if (e && e.name === 'NotFoundError') return '没有找到摄像头设备';
  if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
    return '摄像头需要 HTTPS 安全环境（或 localhost）才能开启';
  }
  return '相机启动失败：' + (e?.message || e);
}

// —— 顶部按钮 ——
$('#btn-flip').addEventListener('click', async () => {
  if (camera?.isRecording?.()) return ui.toast('录像中不能翻转镜头');
  try {
    const info = await camera.switchCamera();
    mirror = info.isFront;
    setFlash(false);
    selVideoId = camera.currentVideoId();
    selAudioId = camera.currentAudioId();
    $('#chk-mirror').checked = mirror;
    await refreshDeviceList();
  } catch { ui.toast('切换摄像头失败（手机才有前后摄像头，桌面请用「设备」选择）'); }
});

// —— 设备选择（外接 USB 摄像头/麦克风；桌面端「翻转」无效时用这个）——
async function initDevices() {
  selVideoId = camera.currentVideoId();
  selAudioId = camera.currentAudioId();
  $('#chk-mirror').checked = mirror;
  await refreshDeviceList();
  navigator.mediaDevices?.addEventListener?.('devicechange', refreshDeviceList);
}

async function refreshDeviceList() {
  const { cameras, mics } = await camera.listDevices();
  fillSelect($('#sel-cam'), cameras, selVideoId);
  fillSelect($('#sel-mic'), mics, selAudioId);
}

function fillSelect(sel, items, currentId) {
  if (!sel) return;
  sel.innerHTML = '';
  if (!items.length) {
    const o = document.createElement('option');
    o.textContent = '（未检测到）';
    sel.append(o);
    return;
  }
  items.forEach((d) => {
    const o = document.createElement('option');
    o.value = d.id;
    o.textContent = d.label;
    if (d.id === currentId) o.selected = true;
    sel.append(o);
  });
}

async function restartCamera(changes) {
  if (camera.isRecording()) return ui.toast('录像中不能切换设备');
  try {
    await camera.start({
      videoDeviceId: changes.video ?? selVideoId,
      audioDeviceId: changes.audio ?? selAudioId
    });
    selVideoId = camera.currentVideoId();
    selAudioId = camera.currentAudioId();
    await refreshDeviceList();
    ui.toast('已切换设备');
  } catch (e) {
    ui.toast('切换设备失败：' + (e?.message || e));
  }
}

$('#btn-devices').addEventListener('click', async () => {
  await refreshDeviceList();
  $('#device-sheet').hidden = false;
});
$('#sheet-close').addEventListener('click', () => { $('#device-sheet').hidden = true; });
$('#device-sheet').addEventListener('click', (e) => {
  if (e.target.id === 'device-sheet') $('#device-sheet').hidden = true;
});
$('#sel-cam').addEventListener('change', (e) => restartCamera({ video: e.target.value }));
$('#sel-mic').addEventListener('change', (e) => restartCamera({ audio: e.target.value }));
$('#chk-mirror').addEventListener('change', (e) => { mirror = e.target.checked; });

$('#btn-close').addEventListener('click', () => {
  if (history.length > 1) history.back();
  else ui.toast('已经是首页啦');
});

$('#btn-face').addEventListener('click', () => {
  const btn = $('#btn-face');
  const on = btn.classList.toggle('on');
  if (on) faceTracker.start(); else { faceTracker.stop(); engine.clearFace(); }
  ui.toast(on ? '自动瘦脸对位：开' : '自动瘦脸对位：关');
});

// —— 补光：后置用硬件手电筒，前置用屏幕白光 ——
let flashOn = false;
function setFlash(on) {
  flashOn = on;
  $('#btn-flash').classList.toggle('on', on);
  if (camera.isFront) {
    $('#flash').classList.toggle('show', on);
  } else {
    $('#flash').classList.remove('show');
    camera.setTorch(on).then((ok) => { if (!ok && on) ui.toast('该设备不支持闪光灯'); });
  }
}
$('#btn-flash').addEventListener('click', () => setFlash(!flashOn));

// —— 标签页 ——
document.querySelectorAll('.tabs button').forEach((b) => {
  b.addEventListener('click', () => ui.showTab(b.dataset.tab));
});

// —— 模式切换 拍照/录像 ——
document.querySelectorAll('.mode-switch button').forEach((b) => {
  b.addEventListener('click', () => {
    if (camera?.isRecording?.()) return;
    mode = b.dataset.mode;
    document.querySelectorAll('.mode-switch button').forEach((x) => x.classList.toggle('active', x === b));
    $('#shutter').classList.toggle('video', mode === 'video');
  });
});

// —— 长按看原图 ——
const cmp = $('#btn-compare');
const cmpDown = (e) => { e.preventDefault(); compare = true; cmp.classList.add('hold'); };
const cmpUp = () => { compare = false; cmp.classList.remove('hold'); };
cmp.addEventListener('pointerdown', cmpDown);
cmp.addEventListener('pointerup', cmpUp);
cmp.addEventListener('pointercancel', cmpUp);
cmp.addEventListener('pointerleave', cmpUp);

// —— 快门 ——
$('#shutter').addEventListener('click', () => {
  if (mode === 'photo') capturePhoto();
  else toggleRecord();
});

function capturePhoto() {
  // 抓当前帧前先确保渲染一次（preserveDrawingBuffer 已开）
  const p = store.get();
  engine.render(video, { ...p, _filterId: filterCode(p.filter), _compare: false }, mirror);
  shutterFx();
  stage.toBlob((blob) => {
    if (!blob) return ui.toast('拍照失败，再试一次');
    const item = gallery.add('photo', blob);
    ui.setThumb(item.url);
    openResult(item);
  }, 'image/jpeg', 0.95);
}

function toggleRecord() {
  if (!camera.isRecording()) {
    camera.startRecording(stage);
    recStart = Date.now();
    $('#shutter').classList.add('recording');
    const timer = $('#rec-timer');
    timer.hidden = false;
    recTimer = setInterval(() => {
      const s = Math.floor((Date.now() - recStart) / 1000);
      timer.textContent = `● ${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
    }, 250);
    ui.toast('开始录像');
  } else {
    clearInterval(recTimer);
    $('#rec-timer').hidden = true;
    $('#shutter').classList.remove('recording');
    camera.stopRecording().then((out) => {
      if (!out || !out.blob.size) return ui.toast('录像失败');
      const item = gallery.add('video', out.blob);
      ui.setThumb(stage.toDataURL('image/jpeg', 0.6));  // 用当前画面做缩略图
      openResult(item);
    });
  }
}

function shutterFx() {
  const f = $('#flash');
  f.classList.add('snap');
  setTimeout(() => f.classList.remove('snap'), 180);
}

// —— 结果浮层 ——
function openResult(item) {
  ui.showResult(item, {
    onRetake: () => {},
    onSave: () => { gallery.download(item); ui.toast('已保存到下载'); },
    onShare: async () => { const ok = await gallery.share(item); if (!ok) ui.toast('已保存（设备不支持直接分享）'); }
  });
}

// 点缩略图回看最近一张
$('#thumb').addEventListener('click', () => {
  if (gallery.latest) openResult(gallery.latest);
});

// 页面隐藏时停掉录制，避免后台异常
document.addEventListener('visibilitychange', () => {
  if (document.hidden && camera?.isRecording?.()) toggleRecord();
});

boot();
