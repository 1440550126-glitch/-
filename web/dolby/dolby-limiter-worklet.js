// AudioWorklet 处理器：前瞻峰值限幅器（look-ahead limiter）。比 WaveShaper 软削波更"干净"：
// 用前瞻延迟在峰值到达前压低增益，快起慢落；threshold/attack/release 可实时调（真机调参），
// 并回传增益衰减(GR)供监看。实验性 + 在主信号路径：需 { limiterWorklet:true } 显式开启，失败回退软削波。
class DolbyLimiterProcessor extends AudioWorkletProcessor {
  static get parameterDescriptors() {
    return [
      { name: 'threshold', defaultValue: 0.95, minValue: 0.1, maxValue: 1 },
      { name: 'attack', defaultValue: 0.4, minValue: 0.01, maxValue: 1 },      // 起音逼近系数（大=快）
      { name: 'release', defaultValue: 0.02, minValue: 0.0005, maxValue: 0.5 } // 释放逼近系数（小=慢）
    ];
  }
  constructor(opts) {
    super();
    this._look = (opts && opts.processorOptions && opts.processorOptions.lookahead) || 64;
    this._buf = null; this._pos = 0; this._gr = 1; this._minGr = 1; this._cnt = 0;
  }
  process(inputs, outputs, params) {
    const inp = inputs[0], out = outputs[0];
    if (!inp || !inp.length || !out || !out.length) return true;
    const ch = inp.length, n = inp[0].length, thr = params.threshold, atk = params.attack, rel = params.release;
    if (!this._buf || this._buf.length !== ch) { this._buf = Array.from({ length: ch }, () => new Float32Array(this._look)); this._pos = 0; }
    for (let i = 0; i < n; i++) {
      const T = thr.length > 1 ? thr[i] : thr[0], A = atk.length > 1 ? atk[i] : atk[0], R = rel.length > 1 ? rel[i] : rel[0];
      let peak = 0; for (let c = 0; c < ch; c++) { const v = Math.abs(inp[c][i]); if (v > peak) peak = v; }
      const target = peak > T ? T / peak : 1;
      this._gr += (target - this._gr) * (target < this._gr ? A : R);
      if (this._gr < this._minGr) this._minGr = this._gr;
      for (let c = 0; c < ch; c++) { const buf = this._buf[c], delayed = buf[this._pos]; buf[this._pos] = inp[c][i]; (out[c] || out[0])[i] = delayed * this._gr; }
      this._pos = (this._pos + 1) % this._look;
    }
    if ((this._cnt += n) >= 2048) { this.port.postMessage(this._minGr); this._minGr = 1; this._cnt = 0; }
    return true;
  }
}
registerProcessor('dolby-limiter', DolbyLimiterProcessor);
