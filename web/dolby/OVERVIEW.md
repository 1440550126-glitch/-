# dolby-audio · 顶层总览（一页速查）

独立、零依赖、纯前端（Web Audio + Canvas/WebGL）的「类杜比」沉浸音效**引擎 + 播放器 + 可视化**套件。
与任何业务解耦：整个 `web/dolby/` 目录可拷到任意网站。详细用法见 [README.md](./README.md)。

## 模块地图（9 个）

| 文件 | 职责 | 关键导出 |
|---|---|---|
| `dolby-audio.js` | **音效引擎**：低频增强 / M/S 展宽 / 耳机 HRTF 环绕 / 人声增强 / 混响 / 单·三段压缩 / 软限幅 / 响度对齐 / 图形均衡 / 电平表 / EQ 曲线 | `DolbyAudio`、`DOLBY_PRESETS`、`EQ_BANDS`、`registerPreset`、`logFreqScale`、`createDolby` |
| `dolby-player.js` | **播放器层**：`<audio>`+引擎+播放列表（传输/循环/随机/事件/锁屏 Media Session） | `DolbyPlayer`、`createPlayer` |
| `dolby-store.js` | **持久化 + 预设导入导出**（localStorage / JSON 分享备份） | `loadPrefs`、`savePrefs`、`applyPrefs`、`autosave`、`exportPreset(s)`、`importPreset(s)` |
| `dolby-abtest.js` | **A/B 盲测打分**：随机藏增强、统计偏好率 | `DolbyABTest`、`createABTest` |
| `dolby-visualizer.js` | **可视化（Canvas2D）**：湍流粒子 + 分色光柱 + 镜头脉冲；含 `AudioReactor`/取色 | `DolbyVisualizer`、`AudioReactor`、`coverColor`、`createVisualizer` |
| `dolby-visualizer-gl.js` | **可视化（WebGL）**：fbm 流体 + 粒子层 + 封面融合；**失败自动回退 Canvas** | `DolbyVisualizerGL`、`createVisualizer`（自动选择） |
| `*.d.ts` | 全量 TypeScript 类型 | — |
| `demo.html` / `player.html` | 两个零构建 Demo（音效处理器 / 播放器+可视化） | — |
| `test/` · `tools/` · `demo-assets/` | 自测（94 断言）· 示例音轨生成器 · 示例 WAV | `npm run dolby:test` |

## 接入 3 步

```js
// ① 给音频接上引擎（音乐网站最常见：<audio>）
import { DolbyAudio } from './dolby/dolby-audio.js';
const dolby = new DolbyAudio({ preset: 'music', analyser: true });
dolby.attachMedia(document.querySelector('audio'));
audioEl.addEventListener('play', () => dolby.resume());   // 用户手势后唤醒

// ② 想要"开箱即用"播放器（列表/上下首/进度/锁屏）就用 DolbyPlayer（可替代 ①）
import { DolbyPlayer } from './dolby/dolby-player.js';
const player = new DolbyPlayer({ tracks: ['/m/a.mp3', '/m/b.mp3'], dolby: { preset: 'music', analyser: true } });
playBtn.onclick = () => player.toggle();

// ③ 加一块跟随节奏的湍流可视化背景（WebGL 优先，自动回退）
import { createVisualizer } from './dolby/dolby-visualizer-gl.js';
createVisualizer(canvas, { dolby: player.dolby }).start();
```

## API 速查

- **引擎**：`setPreset(id|对象)` `setIntensity(0..1)` `setEnabled(on)` `setSpatialMode('speakers'|'headphones')` `setCrossfeed(0..1)` `setMultiband(on)` `setLoudnessMatch(on)` `setLoudnessNorm(LUFS|null)` `setHRIR(buffer)`（个性化 HRTF）`setBass/setAir/setWidth/setReverb/setVocal` `setEQBand(i,dB)`/`setEQ([..])` `snapshotPreset(id,label)` `getLevel()`→`{rms,peak,db,clip}` `getLoudness()` `getIntegratedLoudness()` `getFrequencyResponse()` `getAnalyser()` `dispose()`
- **播放器**：`play/pause/toggle/stop/seek/setVolume/next/prev/load` `setRepeat/'off'|'one'|'all'` `setShuffle` `setPlaylist/add` `on(ev,fn)`（`track/play/pause/ended/time/loaded/error/volume/playlist`）`player.dolby`
- **可视化**：`start/stop/dispose` `setBaseHue(h)` `setCover(img)` `setVizPreset(id)` `setQuality('low'|'mid'|'high')` `analyze()`/`last`→`{bass,mid,treble,energy,beat,bpm}`

## 注意事项（落地必看）

- **自动播放策略**：所有浏览器需用户手势后才出声 → 在点击事件里调用 `dolby.resume()`（`DolbyPlayer.play()` 已内置）。
- **跨域音频/封面**：`attachMedia` 接跨域音频、`setCover`/`coverColor` 用跨域图，需服务端 CORS 头（`<audio|img crossorigin="anonymous">`），否则取不到样本会静音/不混色。
- **严格 CSP**：`media-src 'self'` 会拦截本地选文件的 `blob:`；用 `decodeAudioData`+`attachSource` 规避（见 `demo.js`）。供静态托管的服务端需给 `.wav/.mp3` 等正确 MIME。
- **WebGL**：`createVisualizer` 自动检测，编译失败回退 Canvas2D；粒子层失败仅跳过不影响流体。移动端可用 `{ scale, points }` 降负载。

## 运行 / 验证

```bash
npm start                                   # http://localhost:3000/dolby/demo.html · /player.html
npm run dolby:test                          # 零依赖自测（模拟 Web Audio，94 断言）
```

当前版本：**1.17.0** ·  许可证 MIT
