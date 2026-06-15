// dolby-audio 自测：用模拟 Web Audio API 验证图构建 / 接入 / 控制 / 释放
// 运行：node web/dolby/test/dolby.test.mjs   （零依赖，失败则退出码非 0）
import { DolbyAudio, DOLBY_PRESETS, registerPreset, presetById, createDolby } from '../dolby-audio.js';

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
    createBiquadFilter: () => node({ type: '', frequency: Param(1000), Q: Param(1), gain: Param(0), detune: Param(0) }),
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
ok(typeof lvl.rms === 'number' && typeof lvl.peak === 'number' && typeof lvl.db === 'number', `getLevel 返回 ${JSON.stringify({ rms: +lvl.rms.toFixed(3), peak: lvl.peak, db: +lvl.db.toFixed(1) })}`);

// 8) 自定义预设
registerPreset({ id: 'myroom', label: '我的房间', desc: 't', p: presetById('cinema').p });
ok(presetById('myroom').id === 'myroom', 'registerPreset 注册自定义预设');
d.setPreset('myroom'); ok(d.presetId === 'myroom', '应用注册的自定义预设');
d.setPreset({ id: 'inline', p: presetById('music').p }); ok(d.presetId === 'inline', 'setPreset 接受内联预设对象');

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

console.log(`\n========== dolby-audio：${pass} 项断言全部通过 ✅ ==========`);
