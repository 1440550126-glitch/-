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
