// ============================================================
// dolby-abtest · 杜比效果 A/B 盲测打分（独立 / 零依赖）
// ------------------------------------------------------------
// 把"增强/原声"随机藏在 A、B 两边；先各听一遍，再选更喜欢的，
// 揭晓并统计"偏好增强率"，客观检验调音是否真的更好听
// （而非"开了就觉得好"的心理作用）。
//
//   import { DolbyABTest } from './dolby-abtest.js';
//   const ab = new DolbyABTest(dolby);   // 传入 DolbyAudio（或任何有 setEnabled 的对象）
//   ab.newRound();
//   btnA.onclick = () => ab.audition('A');           // 试听 A（内部据隐藏分配切换）
//   btnB.onclick = () => ab.audition('B');           // 试听 B
//   pickA.onclick = () => show(ab.choose('A'));       // 选 A → 揭晓 + 计分
//   // ab.stats → { rounds, preferEnhanced, rate }
// ============================================================

export class DolbyABTest {
  /**
   * @param {object} dolby            具备 setEnabled(boolean) 的引擎（通常是 DolbyAudio）
   * @param {object} [options]
   * @param {() => number} [options.random=Math.random] 注入随机源（测试可固定）
   */
  constructor(dolby, options = {}) {
    this.dolby = dolby;
    this._rng = options.random || Math.random;
    this.reset();
  }

  reset() { this.rounds = 0; this.preferEnhanced = 0; this._slot = null; this._revealed = true; this._current = null; return this; }

  /** 开新一轮：随机（或用 forceSlot 指定）把"增强"藏到 A/B 之一，回到盲态 */
  newRound(forceSlot) {
    this._slot = forceSlot === 'A' || forceSlot === 'B' ? forceSlot : (this._rng() < 0.5 ? 'A' : 'B');
    this._revealed = false; this._current = null;
    return this;
  }

  /** 试听某一边：该边恰为增强则开启杜比，否则原声；不揭晓 */
  audition(slot) {
    if (!this._slot) this.newRound();
    this._current = slot;
    this.dolby.setEnabled(slot === this._slot);
    return this;
  }

  /** 选择更喜欢的一边：记录并揭晓，返回 { round, picked, enhancedSlot, pickedEnhanced } */
  choose(slot) {
    if (!this._slot) this.newRound();
    const pickedEnhanced = slot === this._slot;
    this.rounds++; if (pickedEnhanced) this.preferEnhanced++;
    this._revealed = true;
    return { round: this.rounds, picked: slot, enhancedSlot: this._slot, pickedEnhanced };
  }

  /** 揭晓后才返回增强所在；盲态返回 null */
  get enhancedSlot() { return this._revealed ? this._slot : null; }
  get current() { return this._current; }
  get stats() {
    return { rounds: this.rounds, preferEnhanced: this.preferEnhanced, rate: this.rounds ? this.preferEnhanced / this.rounds : 0 };
  }
}

export function createABTest(dolby, options) { return new DolbyABTest(dolby, options); }
export default DolbyABTest;
