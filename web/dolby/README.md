# dolby-audio · 杜比风格沉浸音效引擎

一个**独立、零依赖**的纯 Web Audio 母带处理器，给任意网页音频加上"类杜比"的沉浸听感：
低频增强、立体声声场展宽（虚拟环绕）、空间混响、响度优化与软限幅。

> 与本仓库 AI 业务**完全解耦**：整个 `dolby/` 目录可直接拷到任何网站使用。
> 这不是杜比实验室的官方编解码（Dolby Atmos/AC-4 等需商业授权），而是用 Web Audio
> 实时合成的、听感相近的增强引擎。

## 特性

- 🔊 **低频增强** — 低架滤波 + 次谐波激励器，低音更扎实有力
- 🌐 **声场展宽** — M/S 处理保留并增强**原始立体声**，单声道素材安全不抵消
- 🎧 **耳机虚拟环绕** — HRTF 双耳渲染，模拟前置 ±30° + 环绕 ±110° 虚拟音箱，戴耳机也有"音箱在房间里"的外置环绕感
- 🔄 **环绕呼吸** — 缓慢 LFO 调制声场宽度，营造声音流动的包围感
- 🗣 **人声/对白增强** — 提升中置带通，人声/旁白更清晰突出
- 🏛 **空间混响** — 实时合成立体声脉冲响应，影院/音乐厅空间感
- 📊 **动态压缩 + 软削波限制** — 单段或**三段多频带**压缩，提升响度同时防过载
- ⚖️ **响度对齐（Volume Leveler）** — 处理后≈原声响度，开关 A/B 不再"一开就变大声"
- 🎚 **可拖拽图形均衡** — 多段 peaking EQ（`setEQBand/getEQ`），`snapshotPreset()` 一键存为自定义预设
- 📈 **输出电平表 + 均衡曲线** — `getLevel()` 实时电平、`getFrequencyResponse()` 返回 EQ 频响曲线，驱动电平条/曲线图
- 🎛 **干湿混合** — 强度可调、一键 A/B 旁通（等功率交叉淡化，切换不爆音）
- 🎚 **5 档预设 + 自定义** — 标准/影院/音乐/夜间/人声，`registerPreset()` 可扩展
- 💾 **可选偏好持久化** — `dolby-store.js` 助手（引擎本身保持无状态、解耦）
- 🎧 **开箱即用播放器层** — `dolby-player.js`：`<audio>`+引擎+播放列表（上下一首/进度/音量/循环/随机/事件）
- 🔒 **锁屏/通知栏控制** — 自动接入 Media Session（封面/曲目信息 + 上一首/下一首/进度），移动端体验到位
- 🪶 **零依赖 / 零构建** — ES Module，含 TypeScript 类型定义

## 快速开始

### 1) 接 `<audio>` / `<video>`（音乐网站最常见）

```html
<audio id="player" src="/music/song.mp3" controls></audio>
<script type="module">
  import { DolbyAudio } from './dolby/dolby-audio.js';
  const dolby = new DolbyAudio({ preset: 'music' });
  dolby.attachMedia(document.getElementById('player'));   // 接管音频
  // 浏览器要求用户手势后才能出声：
  document.getElementById('player').addEventListener('play', () => dolby.resume());
</script>
```

### 2) 接任意 AudioNode（合成器 / 解码后的 buffer / 麦克风）

```js
import { DolbyAudio } from './dolby/dolby-audio.js';
const dolby = new DolbyAudio({ preset: 'cinema' });
const src = dolby.context.createBufferSource();
src.buffer = await dolby.context.decodeAudioData(arrayBuffer);
dolby.attachSource(src);            // 源 → 引擎 → 扬声器
await dolby.resume(); src.start();
```

### 3) 复用已有 AudioContext / 自己接线

```js
const dolby = new DolbyAudio({ context: myCtx, autoConnect: false });
mySourceNode.connect(dolby.input);
dolby.connect(myCtx.destination);   // 或连到你自己的下游节点
```

## API

构造：`new DolbyAudio(options)`

| 选项 | 默认 | 说明 |
|---|---|---|
| `context` | 自建 | 复用已有的 `AudioContext` |
| `preset` | `'standard'` | 初始预设 id |
| `intensity` | `0.85` | 干湿比 `0..1` |
| `enabled` | `true` | 是否启用（关=直通原声） |
| `autoConnect` | `true` | 自动连到 `context.destination` |
| `analyser` | `false` | 额外挂 `AnalyserNode`，用 `getAnalyser()` 取出做可视化 |
| `spatialMode` | `'speakers'` | 声场渲染：`'speakers'` 外放立体声 / `'headphones'` 耳机 HRTF 虚拟环绕 |
| `multiband` | `false` | 三段多频带压缩（默认单段） |
| `loudnessMatch` | `false` | 响度对齐：处理后≈原声响度 |

方法：

| 方法 | 说明 |
|---|---|
| `attachMedia(el)` | 接 `<audio>`/`<video>`，同一元素只建立一次源节点 |
| `attachSource(node)` | 接任意 `AudioNode` 源 |
| `detach(elOrNode)` | 断开某个已接入的源 |
| `connect(dest?)` | 把输出连到节点（默认 destination） |
| `resume()` | 用户手势后唤醒 AudioContext（返回 Promise） |
| `setPreset(id\|preset)` / `setIntensity(v)` / `setEnabled(on)` / `bypass(on)` | 实时控制（平滑过渡），`setPreset` 也接受自定义预设对象 |
| `setSpatialMode('speakers'\|'headphones')` | 切换外放 / 耳机虚拟环绕（交叉淡化无爆音） |
| `setMultiband(on)` | 三段多频带压缩 ↔ 单段压缩 |
| `setLoudnessMatch(on)` | 开/关响度对齐回路 |
| `setWidth(mult)` / `setBass(dB)` / `setAir(dB)` / `setReverb(mix)` / `setVocal(dB)` | 单项微调（覆盖当前预设） |
| `getAnalyser()` | 取频谱分析器（需构造时 `analyser:true`） |
| `getLevel()` | 取输出电平 `{ rms, peak, db }`，做电平表/动效 |
| `getFrequencyResponse(freqs?)` | 取均衡频响曲线 `{ freqs, magDb }`，画 EQ 曲线图 |
| `state` / `enabled` / `intensity` / `presetId` / `spatialMode` | 只读状态 |
| `dispose({closeContext})` | 释放节点；自建 context 可选关闭 |

顶层还导出 `registerPreset(preset)` 注册自定义预设、`presetById(id)`、`createImpulseResponse(ctx, seconds, decay)`、`logFreqScale(n, min, max)`（对数频率刻度）。

属性 `input` / `output` 暴露入口/出口节点，便于手动接线。

## 预设

| id | 名称 | 适用 |
|---|---|---|
| `standard` | 标准增强 | 均衡，日常聆听 |
| `cinema` | 影院环绕 | 大空间、重低音、强动态 |
| `music` | 音乐厅 | 低音扎实、高音通透 |
| `night` | 夜深人静 | 压缩动态、收敛低音，不扰人 |
| `vocal` | 人声清晰 | 突出中高频，适合旁白/播客 |

预设清单从 `DOLBY_PRESETS` 导出（`[{ id, label, desc, p }]`），可自行增改。

### 自定义预设

```js
import { registerPreset, presetById } from './dolby/dolby-audio.js';
registerPreset({ id: 'club', label: '夜店', desc: '猛低音+宽声场', p: {
  ...presetById('cinema').p, bass: { freq: 80, gain: 9 }, width: 1.8
}});
dolby.setPreset('club');           // 用 id
dolby.setPreset({ id:'tmp', p:{...} }); // 或直接传预设对象
```

## 声场渲染：外放 vs 耳机

```js
dolby.setSpatialMode('headphones');  // 耳机：HRTF 双耳虚拟环绕（外置感更强）
dolby.setSpatialMode('speakers');    // 外放：加宽立体声（默认）
```

- **speakers**：M/S 加宽立体声 + 立体声混响，适合音箱/笔记本外放。
- **headphones**：把加宽后的左右声道经 HRTF 投射到虚拟前置音箱（±30°），混响经虚拟环绕音箱（±110°）投射，戴耳机时声音"跑到头外"，更接近影院环绕。

## 输出电平表

```js
function tick() {
  const { rms, peak, db } = dolby.getLevel();
  meterEl.style.width = Math.min(100, peak * 130) + '%';
  requestAnimationFrame(tick);
}
tick();
```

## 均衡曲线可视化

`getFrequencyResponse()` 返回当前均衡（低架·中频·高架串联）的频响曲线，随 `setBass/setAir`
或预设实时变化，可直接画成 EQ 曲线图：

```js
const { freqs, magDb } = dolby.getFrequencyResponse();   // 默认对数 20–20kHz 200 点
// 也可自定义频点：dolby.getFrequencyResponse(logFreqScale(64, 30, 16000))
for (let i = 0; i < magDb.length; i++) {
  const x = i / (magDb.length - 1) * W;          // 频率（对数轴）
  const y = H / 2 - magDb[i] / 12 * (H / 2);      // 增益 ±12dB → 纵轴
  // lineTo(x, y) ...
}
```

## 图形均衡（可拖拽）与自定义预设

引擎内置一条多段 peaking 图形均衡（频段见 `EQ_BANDS`，默认 7 段），可用作用户可拖拽 EQ：

```js
import { EQ_BANDS } from './dolby/dolby-audio.js';
dolby.setEQBand(0, +6);          // 第 0 段 +6dB
dolby.setEQ([2, 1, 0, 0, -1, 3, 4]);  // 一次设置全部
dolby.getEQ();                   // [{ freq, gain }, ...] 画手柄用
dolby.resetEQ();
```

调好后一键存成自定义预设（含均衡与全部微调），下次直接选用：

```js
import { registerPreset } from './dolby/dolby-audio.js';
const preset = dolby.snapshotPreset('my-room', '我的房间');  // 抓取当前全部设置
registerPreset(preset);
dolby.setPreset('my-room');      // 之后随时套用
```

`demo.html` 的曲线图即是一个可拖拽 EQ：拖圆点调各频段、「重置」「存为预设」一键操作。

## 动态、响度与人声

```js
dolby.setMultiband(true);      // 三段（低<250Hz<中<3.5kHz<高）独立压缩，更扎实
dolby.setLoudnessMatch(true);  // 响度对齐：处理后≈原声响度，A/B 切换更公平
dolby.setVocal(6);             // 人声/对白中置提升 +6dB（旁白、播客更清晰）
```

- **多频带压缩**：用 LR4 分频成低/中/高三段各自压缩再相加，比单段更能"压住"个别频段而不发闷；默认单段，按需打开。
- **响度对齐**：内部用两个分析器持续测量原声与处理后信号的 RMS，自动微调输出增益使两者响度接近——这样开/关杜比做 A/B 时不会被"变大声"误导成"更好听"。
- **人声增强**：提升 M/S 中的中置（Mid）带通，对白/主唱位于中央时尤其有效。

## 偏好持久化（可选）

引擎本身**无状态、不碰存储**；需要记住用户选择时用配套的 `dolby-store.js`：

```js
import { DolbyAudio } from './dolby/dolby-audio.js';
import { loadPrefs, applyPrefs, autosave } from './dolby/dolby-store.js';

const dolby = new DolbyAudio();
applyPrefs(dolby, loadPrefs());   // 启动恢复上次设置
autosave(dolby);                  // 之后任何 set* 调用自动节流保存
```

## 信号链

```
源 → 输入 ─┬─────────────────────────────────────────────── 干声 ─┐
          │                                                       │(等功率
          └─前级→低架EQ→中频峰→高架EQ─┬─→ 音色总线 ──┐            │ 交叉
                  低通→饱和→增益(次谐波)┘             │            │ 淡化)
                              音色总线 → M/S 展宽(±Side·width) ─┐  │
                              音色总线 → 卷积混响 ──────────────┤  │
                                                  动态压缩→软限幅→补偿→湿声┘→ 输出 → 扬声器
```

## 播放器层（DolbyPlayer）

想要"开箱即用"的播放器（而不只是音效处理器）时，用 `dolby-player.js`：它把
`<audio>` + 杜比引擎 + 播放列表打包好，自动处理切歌、循环、随机与自动播放策略。

```js
import { DolbyPlayer } from './dolby/dolby-player.js';

const player = new DolbyPlayer({
  tracks: [
    { src: '/music/a.mp3', title: '歌名 A', artist: '歌手' },
    '/music/b.mp3',                                  // 也可只给字符串
  ],
  dolby: { preset: 'music' },     // 传 options 自建引擎，或传现成 DolbyAudio 实例
  repeat: 'all', shuffle: false, volume: 0.9
});

player.on('track', ({ index, track }) => updateNowPlaying(track));
player.on('time', ({ currentTime, duration }) => updateProgress(currentTime, duration));

playBtn.onclick = () => player.toggle();   // 用户手势里调用（内部会 resume 引擎）
nextBtn.onclick = () => player.next();
player.dolby.setSpatialMode('headphones'); // 引擎全部能力仍可用
```

控制：`play() pause() toggle() stop() seek(s) setVolume(v) next() prev() load(i)`、
`setRepeat('off'|'one'|'all')`、`setShuffle(on)`、`setPlaylist(tracks)`、`add(track)`；
便捷代理 `setPreset/setIntensity/setEnabled/setSpatialMode`，完整能力见 `player.dolby`。

事件：`track` / `play` / `pause` / `ended` / `time` / `loaded` / `error` / `volume` / `playlist`
（`on(ev, fn)` / `off` / `once`）。

**锁屏/通知栏（Media Session）**：在支持的浏览器自动开启，锁屏与通知栏会显示曲目信息、
封面，并提供上一首/下一首/播放/暂停/进度控制。给曲目加 `cover`（或标准 `artwork` 数组）
和 `album` 即可显示封面与专辑：

```js
{ src: '/music/a.mp3', title: '歌名', artist: '歌手', album: '专辑', cover: '/cover/a.jpg' }
```

用 `player.setMediaSession(false)` 可关闭。

## 集成注意事项

- **自动播放策略**：所有浏览器都要求用户手势（点击/触摸）后才能发声。请在用户交互的事件里调用 `resume()`。
- **跨域音频**：用 `attachMedia` 接 `<audio>` 时，若音频是跨域资源，需服务端返回 CORS 头（并给 `<audio crossorigin="anonymous">`），否则 Web Audio 取不到样本会静音。同源音频无此问题。
- **严格 CSP**：若站点 CSP 为 `media-src 'self'`，用户本地选择的文件用 `blob:` 播放会被拦截；改用 `File.arrayBuffer()` + `decodeAudioData()` 走 `attachSource`（本目录 `demo.js` 即此做法）。
- **单声道素材**：M/S 展宽对真立体声有效；纯单声道不会被错误"假立体声"破坏，空间感主要由混响提供。

## 在线 Demo

仓库内已随服务端静态托管，启动后访问：

```
npm start            # 启动本仓库服务
# 音效处理器：  http://localhost:3000/dolby/demo.html
# 播放器层：    http://localhost:3000/dolby/player.html
```

Demo 内置一段合成音乐可直接试听，也能载入你自己的音频做 A/B 对比，带实时频谱、
均衡曲线图、输出电平表、「按住听原声」即时对比按钮，预设/强度/宽度/低音/空间/高频/人声
滑杆，以及「耳机环绕 / 多频带压缩 / 响度对齐」开关。
`player.html` 演示播放器层，内置两段同源 WAV 片段（`demo-assets/`，由
`tools/make-demo-tracks.mjs` 可复现生成）；可用「添加本地文件」把自己的歌加入列表
（站点 CSP 需允许 `blob:` 媒体）。

独立使用时用任意静态服务器即可（如 `npx serve web/dolby`）——注意 ES Module 需经
`http(s)` 加载，直接 `file://` 双击可能被浏览器的模块 CORS 策略拦截。

## 测试

引擎自带零依赖自测（用模拟 Web Audio API 验证图构建/接入/控制/释放）：

```bash
npm run dolby:test       # 在仓库根目录
# 或：node web/dolby/test/dolby.test.mjs
```
