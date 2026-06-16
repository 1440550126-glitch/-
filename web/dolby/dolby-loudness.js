// ============================================================
// dolby-loudness · K 加权 + 响度（LUFS）估计工具（纯函数 / 可测试）
// ------------------------------------------------------------
// 近似 ITU-R BS.1770 的 K 加权（高通 ~38Hz + 高架 ~1.5kHz/+4dB），
// 用于"响度归一化"（向 Dolby Volume 看齐的瞬时响度估计）。
// 注：这是工程近似（瞬时、未做门控），不是认证的 BS.1770 积分响度计。
// ============================================================

/** 构建 K 加权滤波链，返回 { input, output }（两段 biquad 串联） */
export function makeKWeighting(ctx) {
  const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 38; hp.Q.value = 0.5;
  const hs = ctx.createBiquadFilter(); hs.type = 'highshelf'; hs.frequency.value = 1500; hs.gain.value = 4;
  hp.connect(hs);
  return { input: hp, output: hs };
}

/** 由均方值估计响度（LUFS 近似）：L = -0.691 + 10·log10(meanSquare) */
export function lufsFromMeanSquare(ms) {
  return ms > 0 ? -0.691 + 10 * Math.log10(ms) : -Infinity;
}

/** 达到目标 LUFS 所需的线性增益（限幅 ±maxDb） */
export function gainForLufs(currentLufs, targetLufs, maxDb = 12) {
  if (!isFinite(currentLufs)) return 1;
  const db = Math.max(-maxDb, Math.min(maxDb, targetLufs - currentLufs));
  return Math.pow(10, db / 20);
}

// 门控积分响度（BS.1770 / EBU R128 风格）：对一连串测量块（约 400ms 窗口的均方）
// 做绝对门控(-70 LUFS) + 相对门控(-10 LU)，得到整段"积分响度"。
// 注：单/合声道近似，块来自周期性测量，非逐样本 400ms/75% 重叠的严格实现。
export class IntegratedLoudness {
  constructor(maxBlocks = 36000) { this._max = maxBlocks; this.reset(); }
  reset() { this._blocks = []; return this; }
  /** 加入一个测量块的均方值 */
  addBlock(meanSquare) {
    if (meanSquare > 0) { this._blocks.push(meanSquare); if (this._blocks.length > this._max) this._blocks.shift(); }
    return this;
  }
  get count() { return this._blocks.length; }
  /** 双门控积分响度（LUFS）；无有效块返回 -Infinity */
  integrated() {
    const b = this._blocks;
    if (!b.length) return -Infinity;
    const absKept = b.filter((ms) => lufsFromMeanSquare(ms) >= -70);          // 绝对门控
    if (!absKept.length) return -Infinity;
    const meanAbs = absKept.reduce((a, x) => a + x, 0) / absKept.length;
    const relThresh = lufsFromMeanSquare(meanAbs) - 10;                       // 相对门控 -10 LU
    const relKept = absKept.filter((ms) => lufsFromMeanSquare(ms) >= relThresh);
    if (!relKept.length) return -Infinity;
    const meanRel = relKept.reduce((a, x) => a + x, 0) / relKept.length;
    return lufsFromMeanSquare(meanRel);
  }
}
