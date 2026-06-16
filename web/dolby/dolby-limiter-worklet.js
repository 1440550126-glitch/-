// AudioWorklet 处理器：前瞻峰值限幅器（look-ahead limiter）。
// 比 WaveShaper 软削波更"干净"：用前瞻延迟在峰值到达前压低增益，快起慢落。
// 实验性 + 在主信号路径上：默认不启用，需 { limiterWorklet: true } 显式开启；失败回退软削波。
class DolbyLimiterProcessor extends AudioWorkletProcessor {
  static get parameterDescriptors() { return [{ name: 'threshold', defaultValue: 0.95, minValue: 0.1, maxValue: 1 }]; }
  constructor() { super(); this._look = 64; this._buf = null; this._pos = 0; this._gr = 1; }
  process(inputs, outputs, params) {
    const inp = inputs[0], out = outputs[0];
    if (!inp || !inp.length || !out || !out.length) return true;
    const ch = inp.length, n = inp[0].length;
    const tp = params.threshold, thr = tp.length > 1 ? tp[0] : tp[0];
    if (!this._buf || this._buf.length !== ch) { this._buf = Array.from({ length: ch }, () => new Float32Array(this._look)); this._pos = 0; }
    for (let i = 0; i < n; i++) {
      let peak = 0;
      for (let c = 0; c < ch; c++) { const v = Math.abs(inp[c][i]); if (v > peak) peak = v; }
      const target = peak > thr ? thr / peak : 1;             // 需要的增益衰减
      this._gr += (target - this._gr) * (target < this._gr ? 0.4 : 0.02);   // 快起慢落
      for (let c = 0; c < ch; c++) {
        const buf = this._buf[c], delayed = buf[this._pos];   // 前瞻：输出延迟样本
        buf[this._pos] = inp[c][i];
        (out[c] || out[0])[i] = delayed * this._gr;
      }
      this._pos = (this._pos + 1) % this._look;
    }
    return true;
  }
}
registerProcessor('dolby-limiter', DolbyLimiterProcessor);
