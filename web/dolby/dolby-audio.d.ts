// 类型定义 · dolby-audio
// Type definitions for the standalone Dolby-style immersive audio engine.

export interface DolbyPresetParams {
  preGain: number;
  bass: { freq: number; gain: number };
  bassDrive: { amount: number; mix: number };
  mid: { freq: number; gain: number; q: number };
  air: { freq: number; gain: number };
  /** 人声/对白中置提升 dB（可选） */
  vocal?: number;
  width: number;
  motion: { rate: number; depth: number };
  reverb: { mix: number; seconds: number; decay: number };
  comp: { threshold: number; ratio: number; knee: number; attack: number; release: number };
  outGain: number;
  /** 图形均衡各频段增益 dB（可选，与 EQ_BANDS 对应） */
  eq?: number[];
}

export interface EQBand {
  freq: number;
  gain: number;
}

export interface DolbyPreset {
  id: string;
  label: string;
  desc: string;
  p: DolbyPresetParams;
}

export type SpatialMode = 'speakers' | 'headphones';

export interface DolbyOptions {
  context?: AudioContext;
  preset?: string | DolbyPreset;
  intensity?: number;
  enabled?: boolean;
  autoConnect?: boolean;
  analyser?: boolean;
  spatialMode?: SpatialMode;
  multiband?: boolean;
  loudnessMatch?: boolean;
  /** 响度归一化目标 LUFS（如 -14）；不传则关闭 */
  loudnessNorm?: number;
  /** 耳机交叉馈送强度 0..1 */
  crossfeed?: number;
  /** 用 AudioWorklet 做响度测量（脱离主线程），失败回退分析器 */
  worklet?: boolean;
}

export interface DolbyState {
  enabled: boolean;
  preset: string;
  intensity: number;
  spatialMode: SpatialMode;
  multiband: boolean;
  loudnessMatch: boolean;
  loudnessNorm: number | null;
  crossfeed: number;
  supported: boolean;
}

export interface DolbyLevel {
  /** 均方根电平 0..1 */
  rms: number;
  /** 峰值电平 0..1 */
  peak: number;
  /** dBFS */
  db: number;
  /** 是否逼近满刻度（限幅器过载提示） */
  clip: boolean;
}

export interface DolbyFrequencyResponse {
  /** 频率点（Hz） */
  freqs: Float32Array;
  /** 各频点的增益（dB） */
  magDb: Float32Array;
}

export const DOLBY_PRESETS: DolbyPreset[];
export const EQ_BANDS: number[];
export function presetById(id: string): DolbyPreset;
export function registerPreset(preset: DolbyPreset): DolbyPreset;
export function createImpulseResponse(ctx: BaseAudioContext, seconds: number, decay: number): AudioBuffer;
export function logFreqScale(n?: number, min?: number, max?: number): Float32Array;
export function createDolby(options?: DolbyOptions): DolbyAudio;

export class DolbyAudio {
  constructor(options?: DolbyOptions);

  readonly context: AudioContext;
  /** 处理链入口节点 */
  readonly input: GainNode;
  /** 处理链出口节点 */
  readonly output: GainNode;

  attachMedia(el: HTMLMediaElement): MediaElementAudioSourceNode;
  attachSource<T extends AudioNode>(node: T): T;
  detach(elOrNode: HTMLMediaElement | AudioNode): void;
  connect(dest?: AudioNode): this;
  resume(): Promise<void>;

  setPreset(idOrPreset: string | DolbyPreset | DolbyPresetParams, instant?: boolean): this;
  setSpatialMode(mode: SpatialMode, instant?: boolean): this;
  setMultiband(on: boolean, instant?: boolean): this;
  setLoudnessMatch(on: boolean): this;
  setLoudnessNorm(targetLufs: number | null): this;
  setCrossfeed(amount: number): this;
  getLoudness(): number;
  setIntensity(v: number, instant?: boolean): this;
  setEnabled(on: boolean, instant?: boolean): this;
  enable(on: boolean): this;
  bypass(on: boolean): this;

  setWidth(mult: number): this;
  setBass(dB: number): this;
  setAir(dB: number): this;
  setReverb(mix: number): this;
  setVocal(dB: number): this;
  setEQBand(index: number, dB: number, instant?: boolean): this;
  setEQ(gains: number[], instant?: boolean): this;
  getEQ(): EQBand[];
  resetEQ(instant?: boolean): this;
  snapshotPreset(id: string, label?: string, desc?: string): DolbyPreset;

  getAnalyser(): AnalyserNode | null;
  getLevel(): DolbyLevel;
  getFrequencyResponse(freqs?: Float32Array | number[]): DolbyFrequencyResponse;

  readonly enabled: boolean;
  readonly intensity: number;
  readonly presetId: string;
  readonly spatialMode: SpatialMode;
  readonly multiband: boolean;
  readonly loudnessMatch: boolean;
  readonly loudnessNorm: number | null;
  readonly crossfeed: number;
  readonly worklet: boolean;
  readonly state: DolbyState;

  dispose(opts?: { closeContext?: boolean }): void;
}

export default DolbyAudio;
