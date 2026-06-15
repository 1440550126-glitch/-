// ============================================================
// dolby-player · 在 DolbyAudio 之上的轻量播放器层（独立 / 零依赖）
// ------------------------------------------------------------
// 把 <audio> 元素 + 杜比引擎 + 播放列表打包成一个开箱即用的播放器：
//   播放/暂停/上下一首/跳转/音量、单曲/列表循环、随机播放、事件订阅，
//   引擎的全部沉浸音效能力通过 player.dolby 暴露（也有常用代理）。
//
//   import { DolbyPlayer } from './dolby-player.js';
//   const player = new DolbyPlayer({
//     tracks: [{ src: '/music/a.mp3', title: 'A', artist: '...' }, '/music/b.mp3'],
//     dolby: { preset: 'music' }
//   });
//   player.on('track', ({ track }) => render(track));
//   document.querySelector('#play').onclick = () => player.toggle();  // 用户手势
// ============================================================
import { DolbyAudio } from './dolby-audio.js';

const clamp01 = (v) => Math.min(1, Math.max(0, v));
const srcOf = (t) => (typeof t === 'string' ? t : (t && t.src) || '');

export class DolbyPlayer {
  /**
   * @param {object} [options]
   * @param {HTMLMediaElement} [options.audio]   复用已有 <audio>（不传则 new Audio()）
   * @param {DolbyAudio|object} [options.dolby]   现成引擎实例，或构造引擎用的 options
   * @param {Array<string|{src:string}>} [options.tracks] 初始播放列表
   * @param {'off'|'one'|'all'} [options.repeat='off']
   * @param {boolean} [options.shuffle=false]
   * @param {number}  [options.volume=1]
   * @param {string}  [options.crossOrigin]       跨域音频需 'anonymous'
   * @param {boolean} [options.autoplayNext=true] 一曲结束自动下一首
   * @param {boolean} [options.autoload=true]     有列表时自动载入第 0 首
   */
  constructor(options = {}) {
    if (!options.audio && typeof Audio !== 'function') throw new Error('无 <audio> 环境：请传入 options.audio');
    this.audio = options.audio || new Audio();
    this.audio.preload = options.preload || 'auto';
    if (options.crossOrigin !== undefined) this.audio.crossOrigin = options.crossOrigin;

    this.dolby = options.dolby instanceof DolbyAudio ? options.dolby : new DolbyAudio(options.dolby || {});
    this._ownsDolby = !(options.dolby instanceof DolbyAudio);
    this.dolby.attachMedia(this.audio);

    this.tracks = Array.isArray(options.tracks) ? options.tracks.slice() : [];
    this.index = -1;
    this.repeat = ['off', 'one', 'all'].includes(options.repeat) ? options.repeat : 'off';
    this.shuffle = !!options.shuffle;
    this._autoplayNext = options.autoplayNext !== false;
    this.audio.volume = options.volume != null ? clamp01(options.volume) : 1;

    this._handlers = {};
    this._bound = {};
    this._wire();
    if (this.tracks.length && options.autoload !== false) this.load(0, false);
  }

  // ---- 事件：track / play / pause / ended / time / loaded / error / volume / playlist ----
  on(ev, fn) { (this._handlers[ev] || (this._handlers[ev] = [])).push(fn); return this; }
  off(ev, fn) { this._handlers[ev] = (this._handlers[ev] || []).filter((f) => f !== fn); return this; }
  once(ev, fn) { const g = (...a) => { this.off(ev, g); fn(...a); }; return this.on(ev, g); }
  _emit(ev, ...a) { for (const f of (this._handlers[ev] || []).slice()) { try { f(...a); } catch { /* 监听器异常不影响播放 */ } } }

  _wire() {
    const A = this.audio, B = this._bound;
    B.play = () => this._emit('play');
    B.pause = () => this._emit('pause');
    B.time = () => this._emit('time', { currentTime: A.currentTime, duration: A.duration || 0 });
    B.loaded = () => this._emit('loaded', { duration: A.duration || 0 });
    B.ended = () => this._onEnded();
    B.error = () => this._emit('error', A.error);
    B.vol = () => this._emit('volume', A.volume);
    A.addEventListener('play', B.play);
    A.addEventListener('pause', B.pause);
    A.addEventListener('timeupdate', B.time);
    A.addEventListener('loadedmetadata', B.loaded);
    A.addEventListener('ended', B.ended);
    A.addEventListener('error', B.error);
    A.addEventListener('volumechange', B.vol);
  }

  // ---- 播放列表 ----
  setPlaylist(tracks, { autoload = true } = {}) {
    this.tracks = Array.isArray(tracks) ? tracks.slice() : [];
    this.index = -1;
    this._emit('playlist', this.tracks);
    if (autoload && this.tracks.length) this.load(0, false);
    return this;
  }
  add(track) { this.tracks.push(track); this._emit('playlist', this.tracks); return this; }
  get current() { return this.index >= 0 ? this.tracks[this.index] : null; }

  load(i, autoplay = false) {
    if (i < 0 || i >= this.tracks.length) return this;
    this.index = i;
    this.audio.src = srcOf(this.tracks[i]);
    this.audio.load && this.audio.load();
    this._emit('track', { index: i, track: this.tracks[i] });
    if (autoplay) this.play();
    return this;
  }

  // ---- 传输控制 ----
  async play() {
    if (this.index < 0 && this.tracks.length) this.load(0, false);
    await this.dolby.resume();             // 满足自动播放策略
    return this.audio.play();
  }
  pause() { this.audio.pause(); return this; }
  toggle() { return this.playing ? (this.pause(), Promise.resolve()) : this.play(); }
  stop() { this.audio.pause(); this.audio.currentTime = 0; return this; }
  seek(sec) { this.audio.currentTime = sec; return this; }
  setVolume(v) { this.audio.volume = clamp01(v); return this; }

  get volume() { return this.audio.volume; }
  get playing() { return !this.audio.paused; }
  get currentTime() { return this.audio.currentTime; }
  get duration() { return this.audio.duration || 0; }

  next(autoplay = true) {
    if (!this.tracks.length) return this;
    const i = this.shuffle ? this._randIndex() : (this.index + 1) % this.tracks.length;
    return this.load(i, autoplay);
  }
  prev(autoplay = true) {
    if (!this.tracks.length) return this;
    if (this.audio.currentTime > 3) { this.seek(0); return this; }   // 播过 3s 则回开头
    const i = this.shuffle ? this._randIndex() : (this.index - 1 + this.tracks.length) % this.tracks.length;
    return this.load(i, autoplay);
  }
  _randIndex() { if (this.tracks.length <= 1) return 0; let i; do { i = Math.floor(Math.random() * this.tracks.length); } while (i === this.index); return i; }

  setRepeat(mode) { this.repeat = ['off', 'one', 'all'].includes(mode) ? mode : 'off'; return this; }
  setShuffle(on) { this.shuffle = !!on; return this; }

  _onEnded() {
    this._emit('ended', { index: this.index });
    if (this.repeat === 'one') { this.seek(0); this.play(); return; }
    if (!this._autoplayNext) return;
    const last = this.index >= this.tracks.length - 1;
    if (this.shuffle) { this.next(true); return; }
    if (!last) this.next(true);
    else if (this.repeat === 'all') this.load(0, true);   // 否则到列表末尾自然停止
  }

  // ---- 引擎便捷代理（完整能力见 player.dolby） ----
  setPreset(p) { this.dolby.setPreset(p); return this; }
  setIntensity(v) { this.dolby.setIntensity(v); return this; }
  setEnabled(on) { this.dolby.setEnabled(on); return this; }
  setSpatialMode(m) { this.dolby.setSpatialMode(m); return this; }

  get state() {
    return { index: this.index, playing: this.playing, currentTime: this.currentTime, duration: this.duration,
      volume: this.volume, repeat: this.repeat, shuffle: this.shuffle, track: this.current, dolby: this.dolby.state };
  }

  dispose({ closeContext = false } = {}) {
    const A = this.audio, B = this._bound;
    for (const [ev, fn] of [['play', B.play], ['pause', B.pause], ['timeupdate', B.time], ['loadedmetadata', B.loaded], ['ended', B.ended], ['error', B.error], ['volumechange', B.vol]]) {
      A.removeEventListener(ev, fn);
    }
    try { A.pause(); } catch { /* ok */ }
    if (this._ownsDolby) this.dolby.dispose({ closeContext });
    this._handlers = {};
  }
}

export function createPlayer(options) { return new DolbyPlayer(options); }
export default DolbyPlayer;
