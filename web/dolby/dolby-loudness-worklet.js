// AudioWorklet 处理器：在音频线程对（K 加权后）信号做 BS.1770/R128 风格测量——
// 100ms 子块累积、保留最近 4 块组成 400ms 滑窗（100ms 跳 → 75% 重叠），每跳回传该窗均方。
// 把响度测量从主线程挪到音频线程（弱机更稳、更准）。
class DolbyLoudnessProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._hop = Math.max(1, Math.round(sampleRate * 0.1));   // 100ms 帧数（sampleRate 为 worklet 全局）
    this._subSum = 0; this._subN = 0; this._ring = [];
  }
  process(inputs) {
    const input = inputs[0];
    if (input && input.length) {
      const ch = input.length;
      for (let c = 0; c < ch; c++) { const d = input[c]; for (let i = 0; i < d.length; i++) this._subSum += d[i] * d[i]; this._subN += d.length; }
      if (this._subN >= this._hop * ch) {                    // 满 100ms
        this._ring.push({ sum: this._subSum, n: this._subN });
        if (this._ring.length > 4) this._ring.shift();       // 保留 400ms 窗
        let s = 0, n = 0; for (const b of this._ring) { s += b.sum; n += b.n; }
        this.port.postMessage(n ? s / n : 0);                // 400ms 窗均方
        this._subSum = 0; this._subN = 0;
      }
    }
    return true;
  }
}
registerProcessor('dolby-loudness', DolbyLoudnessProcessor);
