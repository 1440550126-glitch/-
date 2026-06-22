// 魔镜魔镜 · 摄像头 / 录制 / 人脸检测
// 全程本地：画面只在浏览器内处理，绝不上传。

export function createCamera(videoEl) {
  let stream = null;
  let facing = 'user';        // user=前置  environment=后置
  let videoTrack = null;
  let audioTrack = null;

  // opts 可为 'user'/'environment' 字符串，或 { facingMode, videoDeviceId, audioDeviceId }
  async function start(opts = {}) {
    if (typeof opts === 'string') opts = { facingMode: opts };
    stop();
    facing = opts.facingMode || facing;
    const videoC = opts.videoDeviceId
      ? { deviceId: { exact: opts.videoDeviceId } }     // 指定设备（外接 USB 摄像头优先）
      : { facingMode: { ideal: facing } };              // 手机前后摄像头
    videoC.width = { ideal: 1280 };
    videoC.height = { ideal: 720 };
    videoC.frameRate = { ideal: 30 };
    const audioC = opts.audioDeviceId ? { deviceId: { exact: opts.audioDeviceId } } : true;
    stream = await navigator.mediaDevices.getUserMedia({ audio: audioC, video: videoC });
    videoTrack = stream.getVideoTracks()[0] || null;
    audioTrack = stream.getAudioTracks()[0] || null;
    videoEl.srcObject = stream;
    videoEl.muted = true;
    videoEl.setAttribute('playsinline', '');
    await videoEl.play().catch(() => {});
    await new Promise((res) => {
      if (videoEl.readyState >= 2) return res();
      videoEl.onloadedmetadata = () => res();
    });
    return { facing, isFront: facing === 'user', videoDeviceId: currentVideoId(), audioDeviceId: currentAudioId() };
  }

  const currentVideoId = () => (videoTrack && videoTrack.getSettings ? videoTrack.getSettings().deviceId : null) || null;
  const currentAudioId = () => (audioTrack && audioTrack.getSettings ? audioTrack.getSettings().deviceId : null) || null;

  // 枚举可用设备（label 需授权后才有值，所以在 start 成功后再调）
  async function listDevices() {
    if (!navigator.mediaDevices?.enumerateDevices) return { cameras: [], mics: [] };
    const all = await navigator.mediaDevices.enumerateDevices();
    const pick = (kind, fallback) => all.filter((d) => d.kind === kind)
      .map((d, i) => ({ id: d.deviceId, label: d.label || `${fallback} ${i + 1}` }));
    return { cameras: pick('videoinput', '摄像头'), mics: pick('audioinput', '麦克风') };
  }

  function stop() {
    if (stream) stream.getTracks().forEach((t) => t.stop());
    stream = null; videoTrack = null; audioTrack = null;
  }

  async function switchCamera() {
    return start(facing === 'user' ? 'environment' : 'user');
  }

  // 后置补光（硬件手电筒，支持的设备才有）
  async function setTorch(on) {
    if (!videoTrack) return false;
    const caps = videoTrack.getCapabilities ? videoTrack.getCapabilities() : {};
    if (!caps.torch) return false;
    try {
      await videoTrack.applyConstraints({ advanced: [{ torch: on }] });
      return true;
    } catch { return false; }
  }

  // —— 录像：抓取处理后的画布视频流 + 麦克风音轨 ——
  let recorder = null, chunks = [], recMime = '';

  function pickMime() {
    const list = [
      'video/mp4;codecs=h264,aac',
      'video/mp4',
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm'
    ];
    return list.find((m) => window.MediaRecorder && MediaRecorder.isTypeSupported(m)) || '';
  }

  function startRecording(glCanvas) {
    const canvasStream = glCanvas.captureStream(30);
    const tracks = canvasStream.getVideoTracks();
    if (audioTrack) tracks.push(audioTrack);
    const mixed = new MediaStream(tracks);
    recMime = pickMime();
    recorder = new MediaRecorder(mixed, recMime ? { mimeType: recMime, videoBitsPerSecond: 8_000_000 } : undefined);
    chunks = [];
    recorder.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    recorder.start(100);
    return true;
  }

  function stopRecording() {
    return new Promise((resolve) => {
      if (!recorder) return resolve(null);
      recorder.onstop = () => {
        const type = recMime || 'video/webm';
        const blob = new Blob(chunks, { type });
        recorder = null; chunks = [];
        resolve({ blob, type });
      };
      recorder.stop();
    });
  }

  const isRecording = () => !!recorder && recorder.state === 'recording';

  return {
    start, stop, switchCamera, setTorch,
    startRecording, stopRecording, isRecording,
    listDevices, currentVideoId, currentAudioId,
    get facing() { return facing; },
    get isFront() { return facing === 'user'; }
  };
}

// —— 人脸检测（原生 FaceDetector，支持则用于瘦脸自动对位；不支持则回退中轴）——
export function createFaceTracker(videoEl, onFace) {
  let detector = null, raf = 0, running = false, last = 0;
  if ('FaceDetector' in window) {
    try { detector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 1 }); } catch { detector = null; }
  }

  async function tick(ts) {
    raf = requestAnimationFrame(tick);
    if (!running || !detector || ts - last < 280) return;   // ~3.5fps 足够定位
    last = ts;
    const vw = videoEl.videoWidth, vh = videoEl.videoHeight;
    if (!vw || !vh) return;
    try {
      const faces = await detector.detect(videoEl);
      if (faces && faces.length) {
        const b = faces[0].boundingBox;
        // 转成 uv（注意纹理已翻转 Y：图像顶部对应 uv.y=1）
        onFace({
          cx: (b.x + b.width / 2) / vw,
          cy: 1 - (b.y + b.height / 2) / vh,
          rx: (b.width / 2) / vw,
          ry: (b.height / 2) / vh
        });
      } else {
        onFace(null);
      }
    } catch { /* 忽略单帧失败 */ }
  }

  return {
    supported: !!detector,
    start() { if (!detector) return; running = true; raf = requestAnimationFrame(tick); },
    stop() { running = false; cancelAnimationFrame(raf); }
  };
}
