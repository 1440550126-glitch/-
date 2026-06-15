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
}

export interface DolbyState {
  enabled: boolean;
  preset: string;
  intensity: number;
  spatialMode: SpatialMode;
  multiband: boolean;
  loudnessMatch: boolean;
  supported: boolean;
}

export interface DolbyLevel {
  /** 均方根电平 0..1 */
  rms: number;
  /** 峰值电平 0..1 */
  peak: number;
  /** dBFS */
  db: number;
}

export const DOLBY_PRESETS: DolbyPreset[];
export function presetById(id: string): DolbyPreset;
export function registerPreset(preset: DolbyPreset): DolbyPreset;
export function createImpulseResponse(ctx: BaseAudioContext, seconds: number, decay: number): AudioBuffer;
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
  setIntensity(v: number, instant?: boolean): this;
  setEnabled(on: boolean, instant?: boolean): this;
  enable(on: boolean): this;
  bypass(on: boolean): this;

  setWidth(mult: number): this;
  setBass(dB: number): this;
  setAir(dB: number): this;
  setReverb(mix: number): this;
  setVocal(dB: number): this;

  getAnalyser(): AnalyserNode | null;
  getLevel(): DolbyLevel;

  readonly enabled: boolean;
  readonly intensity: number;
  readonly presetId: string;
  readonly spatialMode: SpatialMode;
  readonly multiband: boolean;
  readonly loudnessMatch: boolean;
  readonly state: DolbyState;

  dispose(opts?: { closeContext?: boolean }): void;
}

export default DolbyAudio;
