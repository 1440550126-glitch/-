// dolby-audio 自测：用模拟 Web Audio API 验证图构建 / 接入 / 控制 / 释放
// 运行：node web/dolby/test/dolby.test.mjs   （零依赖，失败则退出码非 0）
import { DolbyAudio, DOLBY_PRESETS, registerPreset, presetById, createDolby, logFreqScale, EQ_BANDS } from '../dolby-audio.js';

let pass = 0;
const ok = (cond, msg) => { if (!cond) { console.error('  ❌ ' + msg); throw new Error(msg); } pass++; console.log('  ✅ ' + msg); };

// —— 模拟 Web Audio API ——
let connects = 0, disconnects = 0, mediaSrcCount = 0;
const Param = (v = 0) => ({ value: v, setTargetAtTime(x) { this.value = x; }, setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {} });
const node = (extra = {}) => ({ connect(d) { connects++; return d; }, disconnect() { disconnects++; }, ...extra });
function makeCtx() {
  return {
    sampleRate: 48000, currentTime: 0, state: 'suspended', destination: node(),
    resume() { this.state = 'running'; return Promise.resolve(); },
    close() { this.state = 'closed'; return Promise.resolve(); },
    createGain: () => node({ gain: Param(1) }),
    createBiquadFilter: () => { const f = node({ type: '', frequency: Param(1000), Q: Param(1), gain: Param(0), detune: Param(0) }); f.getFrequencyResponse = (freqs, mag) => { const a = Math.pow(10, f.gain.value / 20); for (let i = 0; i < mag.length; i++) mag[i] = a; }; return f; },
    createWaveShaper: () => node({ curve: null, oversample: 'none' }),
    createChannelSplitter: () => node(),
    createChannelMerger: () => node(),
    createStereoPanner: () => node({ pan: Param(0) }),
    createPanner: () => node({ panningModel: '', distanceModel: '', positionX: Param(0), positionY: Param(0), positionZ: Param(0), setPosition() {} }),
    createConvolver: () => node({ buffer: null }),
    createDynamicsCompressor: () => node({ threshold: Param(-24), ratio: Param(12), knee: Param(30), attack: Param(0.003), release: Param(0.25) }),
    createOscillator: () => node({ type: '', frequency: Param(1), detune: Param(0), start() {}, stop() {} }),
    createAnalyser: () => node({ fftSize: 2048, smoothingTimeConstant: 0.8, frequencyBinCount: 1024, getByteFrequencyData() {}, getFloatTimeDomainData(a) { a.fill(0.25); } }),
    createBuffer: (ch, len) => ({ numberOfChannels: ch, length: len, getChannelData: () => new Float32Array(len) }),
    createMediaElementSource: () => { mediaSrcCount++; return node(); }
  };
}

function makeAudio() {
  const L = {};
  return {
    paused: true, currentTime: 0, duration: 120, volume: 1, src: '', crossOrigin: null, preload: '', error: null,
    addEventListener(ev, fn) { (L[ev] || (L[ev] = [])).push(fn); },
    removeEventListener(ev, fn) { L[ev] = (L[ev] || []).filter((f) => f !== fn); },
    play() { this.paused = false; this._fire('play'); return Promise.resolve(); },
    pause() { this.paused = true; this._fire('pause'); },
    load() {},
    _fire(ev) { for (const f of (L[ev] || []).slice()) f(); },
    _count(ev) { return (L[ev] || []).length; }
  };
}

console.log('dolby-audio 自测');

// 1) 构建
const ctx = makeCtx();
const d = new DolbyAudio({ context: ctx, analyser: true });
ok(connects > 30, `图构建完成（${connects} 个连接）`);
ok(!!d.getAnalyser(), '频谱分析器已挂载');
ok(d.input && d.output, '暴露 input/output 节点');
ok(d.state.preset === 'standard' && d.state.spatialMode === 'speakers', `默认状态正确：${JSON.stringify(d.state)}`);

// 2) 源接入：同一 media 元素只建一次源
const el = {};
d.attachMedia(el); d.attachMedia(el);
ok(mediaSrcCount === 1, 'attachMedia 对同一元素只建立一次源节点');
d.attachSource(node());
ok(true, 'attachSource 接入任意 AudioNode');

// 3) 唤醒
await d.resume();
ok(ctx.state === 'running', 'resume 唤醒 AudioContext');

// 4) 全部预设
for (const p of DOLBY_PRESETS) { d.setPreset(p.id); ok(d.presetId === p.id, `应用预设 ${p.label}(${p.id})`); }

// 5) 声场模式
d.setSpatialMode('headphones'); ok(d.spatialMode === 'headphones', '切换到耳机 HRTF 虚拟环绕');
d.setSpatialMode('speakers'); ok(d.spatialMode === 'speakers', '切回扬声器立体声');

// 6) 强度 / 开关 / 微调
d.setIntensity(0.5); ok(Math.abs(d.intensity - 0.5) < 1e-9, 'setIntensity 生效');
d.setEnabled(false); ok(!d.enabled, 'setEnabled(false) 旁通');
d.setEnabled(true); d.bypass(true); ok(!d.enabled, 'bypass(true) 等价关闭'); d.bypass(false);
d.setWidth(1.9); d.setBass(6); d.setAir(3); d.setReverb(0.2);
ok(true, '单项微调 setWidth/Bass/Air/Reverb 不抛错');

// 7) 电平表
const lvl = d.getLevel();
ok(typeof lvl.rms === 'number' && typeof lvl.peak === 'number' && typeof lvl.db === 'number' && typeof lvl.clip === 'boolean' && lvl.clip === false, `getLevel 返回 ${JSON.stringify({ rms: +lvl.rms.toFixed(3), peak: lvl.peak, db: +lvl.db.toFixed(1), clip: lvl.clip })}`);

// 7b) 频响曲线
const fs = logFreqScale(64);
ok(fs.length === 64 && fs[0] >= 20 && fs[fs.length - 1] <= 20000, `logFreqScale 生成对数频率刻度 [${fs[0].toFixed(0)}..${fs[fs.length - 1].toFixed(0)}Hz]`);
const fr = d.getFrequencyResponse(fs);
ok(fr.freqs.length === 64 && fr.magDb.length === 64 && Array.prototype.every.call(fr.magDb, Number.isFinite), 'getFrequencyResponse 返回有限 dB 曲线');
d.setAir(0); d.setBass(0); const flat = d.getFrequencyResponse(logFreqScale(8)).magDb[0];
d.setBass(10); const boosted = d.getFrequencyResponse(logFreqScale(8)).magDb[0];
ok(boosted > flat + 5, `频响随低音增益上升（${flat.toFixed(1)}→${boosted.toFixed(1)}dB）`);

// 7c) 图形均衡（可拖拽 EQ）
ok(EQ_BANDS.length === d.getEQ().length && d.getEQ().every((b) => b.gain === 0), `图形均衡 ${EQ_BANDS.length} 段，初始全 0dB`);
const eqFlat = d.getFrequencyResponse(logFreqScale(8)).magDb[3];
d.setEQBand(0, 9); ok(d.getEQ()[0].gain === 9, 'setEQBand 调节单段');
ok(d.getFrequencyResponse(logFreqScale(8)).magDb[3] > eqFlat, '频响曲线包含图形均衡');
d.resetEQ(); ok(d.getEQ().every((b) => b.gain === 0), 'resetEQ 归零');
d.setEQ([1, 2, 3, 0, -2, -1, 0]); ok(d.getEQ()[2].gain === 3 && d.getEQ()[4].gain === -2, 'setEQ 批量设置');
const snap = d.snapshotPreset('mysnap', '我的快照');
ok(snap.id === 'mysnap' && Array.isArray(snap.p.eq) && snap.p.eq[2] === 3, 'snapshotPreset 含当前均衡');
registerPreset(snap); d.setPreset('standard'); ok(d.getEQ().every((b) => b.gain === 0), 'setPreset（无 eq）复位均衡');
d.setPreset('mysnap'); ok(d.getEQ()[2].gain === 3, 'setPreset 应用快照预设的均衡');
d.resetEQ();

// 8) 自定义预设
registerPreset({ id: 'myroom', label: '我的房间', desc: 't', p: presetById('cinema').p });
ok(presetById('myroom').id === 'myroom', 'registerPreset 注册自定义预设');
d.setPreset('myroom'); ok(d.presetId === 'myroom', '应用注册的自定义预设');
d.setPreset({ id: 'inline', p: presetById('music').p }); ok(d.presetId === 'inline', 'setPreset 接受内联预设对象');

// 8b) 多频带压缩 / 人声增强 / 响度对齐
d.setMultiband(true); ok(d.multiband, '开启三段多频带压缩');
d.setMultiband(false); ok(!d.multiband, '切回单段压缩');
d.setVocal(6); ok(true, 'setVocal 人声增强不抛错');
d.setLoudnessMatch(true); ok(d.loudnessMatch, '开启响度对齐（内部测量回路）');
d._updateMatch(); ok(true, '响度对齐测量一次不抛错');
d.setLoudnessMatch(false); ok(!d.loudnessMatch, '关闭响度对齐');
ok('multiband' in d.state && 'loudnessMatch' in d.state, `state 含新字段：${JSON.stringify(d.state)}`);

// 9) 工厂 + 释放
const d2 = createDolby({ context: makeCtx(), autoConnect: false });
ok(d2 instanceof DolbyAudio, 'createDolby 工厂函数');
const before = disconnects; d.dispose({ closeContext: true });
ok(disconnects > before, `dispose 断开节点（+${disconnects - before}）`);
ok(ctx.state !== 'closed', 'dispose 不关闭外部传入的 context（只释放节点）');

// 自建 context：dispose(closeContext) 才会真正关闭
globalThis.window = { AudioContext: function () { return makeCtx(); } };
const owned = new DolbyAudio();
const oc = owned.context;
owned.dispose({ closeContext: true });
ok(oc.state === 'closed', 'dispose(closeContext) 关闭自建 context');
delete globalThis.window;

// 10) 持久化助手 dolby-store
globalThis.localStorage = (() => { let m = {}; return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: (k) => { delete m[k]; } }; })();
const store = await import('../dolby-store.js');
const p0 = store.loadPrefs();
ok(p0.preset === 'standard' && p0.spatialMode === 'speakers', 'loadPrefs 无数据时返回默认');
const sd = createDolby({ context: makeCtx() });
sd.setPreset('cinema'); sd.setSpatialMode('headphones'); sd.setIntensity(0.6); sd.setMultiband(true);
ok(store.savePrefs(store.snapshot(sd)), 'savePrefs 写入当前快照');
const p1 = store.loadPrefs();
ok(p1.preset === 'cinema' && p1.spatialMode === 'headphones' && Math.abs(p1.intensity - 0.6) < 1e-9 && p1.multiband, `loadPrefs 读回快照：${JSON.stringify(p1)}`);
const sd2 = createDolby({ context: makeCtx() });
store.applyPrefs(sd2, p1);
ok(sd2.presetId === 'cinema' && sd2.spatialMode === 'headphones' && sd2.multiband, 'applyPrefs 套用到新实例');
store.autosave(sd2, 'dolby:prefs', 40); sd2.setPreset('music');
await new Promise((r) => setTimeout(r, 80));
ok(store.loadPrefs().preset === 'music', 'autosave 自动持久化 set* 调用');
sd.dispose(); sd2.dispose();

// 11) DolbyPlayer 播放器层
const { DolbyPlayer, createPlayer } = await import('../dolby-player.js');
const audio = makeAudio();
const pdolby = new DolbyAudio({ context: makeCtx(), autoConnect: false });
const player = new DolbyPlayer({ audio, dolby: pdolby, tracks: [{ src: 'a.mp3', title: 'A' }, 'b.mp3', { src: 'c.mp3' }] });
ok(player.dolby === pdolby, 'DolbyPlayer 复用传入的引擎实例');
ok(player.index === 0 && audio.src === 'a.mp3', 'autoload 载入第 0 首');
let trackEv = null; player.on('track', (e) => { trackEv = e; });
player.load(1); ok(player.index === 1 && audio.src === 'b.mp3' && trackEv.index === 1, 'load 切歌并触发 track 事件（支持字符串轨）');
await player.play(); ok(player.playing, 'play 播放');
player.pause(); ok(!player.playing, 'pause 暂停');
player.next(false); ok(player.index === 2, 'next 下一首');
player.next(false); ok(player.index === 0, 'next 末尾回环到第 0 首');
player.prev(false); ok(player.index === 2, 'prev 上一首回环');
audio.currentTime = 5; player.prev(false); ok(player.index === 2 && audio.currentTime === 0, 'prev 播过 3s 回到本曲开头');
player.setRepeat('one'); player.load(1); audio.currentTime = 10; audio._fire('ended');
ok(player.index === 1 && audio.currentTime === 0, 'repeat=one 结束后重播本曲');
player.setRepeat('all'); player.load(2); audio._fire('ended'); ok(player.index === 0, 'repeat=all 末尾结束回到第 0 首');
player.setVolume(0.5); ok(audio.volume === 0.5, 'setVolume 生效');
player.add('d.mp3'); ok(player.tracks.length === 4, 'add 追加曲目');
player.dispose(); ok(audio._count('play') === 0, 'dispose 解绑音频事件');
const p2 = createPlayer({ audio: makeAudio(), dolby: new DolbyAudio({ context: makeCtx(), autoConnect: false }) });
ok(p2 instanceof DolbyPlayer, 'createPlayer 工厂函数'); p2.dispose();

// 12) Media Session 集成
const handlers = {}; let posState = null;
globalThis.MediaMetadata = class { constructor(o) { Object.assign(this, o); } };
const navDesc = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
Object.defineProperty(globalThis, 'navigator', { configurable: true, writable: true, value: { mediaSession: { metadata: null, playbackState: 'none', setActionHandler(a, fn) { handlers[a] = fn; }, setPositionState(s) { posState = s; } } } });
const ma = makeAudio();
const mp = new DolbyPlayer({ audio: ma, dolby: new DolbyAudio({ context: makeCtx(), autoConnect: false }), tracks: [{ src: 'a.mp3', title: 'A', artist: 'X', cover: '/c.png' }, { src: 'b.mp3', title: 'B' }] });
ok(typeof handlers.play === 'function' && typeof handlers.nexttrack === 'function' && typeof handlers.seekto === 'function', 'Media Session 注册动作处理器');
ok(navigator.mediaSession.metadata?.title === 'A' && navigator.mediaSession.metadata.artist === 'X', 'track 载入设置 metadata（标题/艺人）');
ma.duration = 200; ma.currentTime = 50; ma._fire('timeupdate'); ok(posState?.duration === 200 && posState.position === 50, 'timeupdate 同步 setPositionState');
ma._fire('play'); ok(navigator.mediaSession.playbackState === 'playing', "'play' 事件更新 playbackState");
ma._fire('pause'); ok(navigator.mediaSession.playbackState === 'paused', "'pause' 事件更新 playbackState");
handlers.seekto({ seekTime: 30 }); ok(ma.currentTime === 30, 'seekto 动作跳转');
handlers.nexttrack(); ok(mp.index === 1 && navigator.mediaSession.metadata.title === 'B', 'nexttrack 动作切歌并更新 metadata');
mp.setMediaSession(false); ok(navigator.mediaSession.playbackState === 'none' && handlers.play === null, 'setMediaSession(false) 清理处理器与状态');
await Promise.resolve();
mp.dispose();
if (navDesc) Object.defineProperty(globalThis, 'navigator', navDesc); else delete globalThis.navigator;
delete globalThis.MediaMetadata;

// 13) A/B 盲测打分
const { DolbyABTest, createABTest } = await import('../dolby-abtest.js');
const abDolby = new DolbyAudio({ context: makeCtx(), autoConnect: false });
const ab = new DolbyABTest(abDolby, { random: () => 0.2 });   // <0.5 → 'A'
ab.newRound();
ok(ab.enhancedSlot === null, '盲态不泄露增强位置');
ab.audition('A'); ok(abDolby.enabled === true, '试听增强位（A）→ 开启杜比');
ab.audition('B'); ok(abDolby.enabled === false, '试听另一位（B）→ 原声');
const r1 = ab.choose('A');
ok(r1.pickedEnhanced && r1.enhancedSlot === 'A' && ab.enhancedSlot === 'A', '选中增强：记录并揭晓');
ok(ab.stats.rounds === 1 && ab.stats.preferEnhanced === 1 && ab.stats.rate === 1, '统计：1 轮全偏好增强');
ab.newRound('B'); ab.choose('A');
ok(ab.stats.rounds === 2 && ab.stats.preferEnhanced === 1 && Math.abs(ab.stats.rate - 0.5) < 1e-9, '第二轮选错：偏好率降到 50%');
ab.reset(); ok(ab.stats.rounds === 0 && ab.enhancedSlot === null, 'reset 清零');
ok(createABTest(abDolby) instanceof DolbyABTest, 'createABTest 工厂函数');
abDolby.dispose();

// 14) 音频湍流可视化（频谱分析 / 节拍）
const { DolbyVisualizer } = await import('../dolby-visualizer.js');
const vAn = { fftSize: 1024, frequencyBinCount: 256, _v: new Uint8Array(256), getByteFrequencyData(a) { a.set(this._v); } };
const vCanvas = { clientWidth: 320, clientHeight: 200, width: 0, height: 0, getContext: () => ({ setTransform() {} }) };
const viz = new DolbyVisualizer(vCanvas, { analyser: vAn, particles: 12 });
ok(viz.particles.length === 12, '可视化初始化粒子');
vAn._v.fill(0); const a0 = viz.analyze(); ok(a0.energy === 0 && !a0.beat, '静音：无能量无节拍');
for (let i = 0; i < 20; i++) vAn._v[i] = 250; const a1 = viz.analyze();
ok(a1.bass > 0.5 && a1.beat, '强低频：触发节拍');
viz.setBaseHue(200); ok(viz.baseHue === 200, 'setBaseHue');
viz.start(); viz.stop(); viz.dispose(); ok(!viz.running, 'start/stop/dispose（无 rAF 环境）不抛错');
const { AudioReactor } = await import('../dolby-visualizer.js');
const rb = new AudioReactor(vAn);                 // vAn 低频仍强（前面已填 250）
let bpmV = 0; for (const tm of [1000, 1500, 2000, 2500]) bpmV = rb.read(tm).bpm;   // 每 500ms 一拍 → 120
ok(bpmV === 120, `AudioReactor BPM 估计=${bpmV}`);
const viz2 = new DolbyVisualizer(vCanvas, { analyser: vAn, particles: 4 });
const fakeImg = {}; viz2.setCover(fakeImg); ok(viz2._cover === fakeImg, 'setCover 设置封面背景');
viz2.clearCover(); ok(viz2._cover === null, 'clearCover 清除封面'); viz2.dispose();
const { VIZ_PRESETS, VIZ_QUALITY } = await import('../dolby-visualizer.js');
const viz3 = new DolbyVisualizer(vCanvas, { analyser: vAn, vizPreset: 'ember', quality: 'low' });
ok(viz3.vizPreset === 'ember' && viz3.quality === 'low', 'options.vizPreset/quality 生效');
ok(viz3.particleCount === VIZ_QUALITY.low.particles, `low 档粒子数=${viz3.particleCount}`);
viz3.setVizPreset('aurora'); ok(viz3.baseHue === VIZ_PRESETS.find((p) => p.id === 'aurora').baseHue, 'setVizPreset 改配色');
viz3.setQuality('high'); ok(viz3.particleCount === VIZ_QUALITY.high.particles, 'setQuality 改粒子数'); viz3.dispose();

// 15) 预设导入/导出
const jsonP = store.exportPreset({ id: 'x', label: 'X', p: { bass: { gain: 6 } } });
ok(typeof jsonP === 'string' && JSON.parse(jsonP).id === 'x', 'exportPreset → JSON');
ok(store.importPreset(jsonP).p.bass.gain === 6, 'importPreset ← JSON');
let badThrew = false; try { store.importPreset('{"oops":1}'); } catch { badThrew = true; }
ok(badThrew, 'importPreset 校验非法结构');
const jsonAll = store.exportPresets([{ id: 'a', p: {} }, { id: 'b', p: {} }]);
ok(store.importPresets(jsonAll).length === 2, 'exportPresets/importPresets 往返');

// 16) WebGL 可视化工厂：无 WebGL 时自动回退
const { createVisualizer } = await import('../dolby-visualizer-gl.js');
const mkAn = () => ({ fftSize: 1024, frequencyBinCount: 128, getByteFrequencyData(a) { a.fill(0); } });
const glCanvas = { clientWidth: 320, clientHeight: 200, width: 0, height: 0, getContext: (ty) => ty === '2d' ? ({ setTransform() {} }) : null };
const vAuto = createVisualizer(glCanvas, { analyser: mkAn(), particles: 8 });
ok(vAuto instanceof DolbyVisualizer, '无 WebGL 时 createVisualizer 回退到 Canvas2D');
let glThrew = false; try { createVisualizer(glCanvas, { renderer: 'webgl', analyser: mkAn() }); } catch { glThrew = true; }
ok(glThrew, "renderer:'webgl' 在无 WebGL 时抛错（不静默降级）");
vAuto.dispose();

console.log(`\n========== dolby-audio：${pass} 项断言全部通过 ✅ ==========`);
