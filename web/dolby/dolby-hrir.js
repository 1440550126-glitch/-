// ============================================================
// dolby-hrir · HRIR 数据集 → 双耳脉冲响应（个性化 HRTF 实用管线）
// ------------------------------------------------------------
// ⚠️ 不内置 SOFA(HDF5) 二进制解析（HDF5 解析庞大且难在本环境验证）。
// 请把 SOFA 离线转成下述简单格式后再用（社区有 sofa→json/wav 转换脚本）：
//   set = {
//     sampleRate: 48000,
//     dirs: [{ az, el }, ...],         // 方位角(度,+右)/仰角
//     ir:   [[Float32 L, Float32 R], ...]   // 每个方位的左右耳 HRIR，与 dirs 对应
//   }
// buildBinauralIR 取最近的左前/右前 HRIR 组成 4 声道"真立体声"卷积响应，
// 喂给 DolbyAudio.setHRIR() 即得个性化双耳。
// ============================================================

const wrap180 = (d) => { d = ((d % 360) + 360) % 360; return d > 180 ? d - 360 : d; };

/** 在 dirs 中找最接近 (az,el) 的索引（按角度距离） */
export function nearestDir(dirs, az, el = 0) {
  let best = 0, bd = Infinity;
  for (let i = 0; i < dirs.length; i++) {
    const da = wrap180(dirs[i].az - az), de = (dirs[i].el || 0) - el;
    const d = da * da + de * de;
    if (d < bd) { bd = d; best = i; }
  }
  return best;
}

/**
 * 由 HRIR 集渲染 4 声道双耳卷积响应（真立体声）：
 * 左输入→左前方位(默认 -30°) 的 (L,R) 耳，右输入→右前方位(+30°) 的 (L,R) 耳。
 * @returns {AudioBuffer} 4 声道 [Lin→Lear, Lin→Rear, Rin→Lear, Rin→Rear]
 */
export function buildBinauralIR(ctx, set, frontAz = 30) {
  if (!set || !Array.isArray(set.dirs) || !Array.isArray(set.ir) || !set.dirs.length) throw new Error('无效 HRIR 集');
  const li = nearestDir(set.dirs, -frontAz), ri = nearestDir(set.dirs, frontAz);
  const lIR = set.ir[li], rIR = set.ir[ri];
  const len = Math.max(lIR[0].length, lIR[1].length, rIR[0].length, rIR[1].length);
  const rate = set.sampleRate || ctx.sampleRate;
  const buf = ctx.createBuffer(4, len, rate);
  const put = (ch, src) => { const d = buf.getChannelData(ch); for (let i = 0; i < src.length; i++) d[i] = src[i]; };
  put(0, lIR[0]); put(1, lIR[1]); put(2, rIR[0]); put(3, rIR[1]);
  return buf;
}
