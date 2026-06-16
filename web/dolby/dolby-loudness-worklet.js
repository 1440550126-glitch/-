// AudioWorklet 处理器：在音频线程计算（K 加权后）信号的均方值并回传主线程，
// 把响度测量从主线程挪到音频线程（弱机更稳、更准）。主线程 addModule 后创建节点。
class DolbyLoudnessProcessor extends AudioWorkletProcessor {
  constructor() { super(); this._sum = 0; this._n = 0; }
  process(inputs) {
    const input = inputs[0];
    if (input && input.length) {
      for (let c = 0; c < input.length; c++) {
        const d = input[c];
        for (let i = 0; i < d.length; i++) this._sum += d[i] * d[i];
        this._n += d.length;
      }
      if (this._n >= 9600) {                 // 累计约 100ms 样本后回传一次均方
        this.port.postMessage(this._sum / this._n);
        this._sum = 0; this._n = 0;
      }
    }
    return true;                             // 持续运行
  }
}
registerProcessor('dolby-loudness', DolbyLoudnessProcessor);
