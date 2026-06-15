// 类型定义 · dolby-visualizer
import type { DolbyAudio } from './dolby-audio';

export interface VisualizerOptions {
  analyser?: AnalyserNode;
  dolby?: DolbyAudio;
  node?: AudioNode;
  context?: BaseAudioContext;
  fftSize?: number;
  baseHue?: number;
  hueRange?: number;
  particles?: number;
  background?: [number, number, number];
}

export interface AudioFrame {
  bass: number;
  mid: number;
  treble: number;
  energy: number;
  beat: boolean;
  /** 估计的每分钟节拍数（0 表示尚不确定） */
  bpm: number;
}

export class AudioReactor {
  constructor(analyser: AnalyserNode);
  readonly analyser: AnalyserNode;
  readonly data: Uint8Array;
  read(now?: number): AudioFrame;
}

export interface CoverColor {
  r: number;
  g: number;
  b: number;
  hue: number;
}

export class DolbyVisualizer {
  constructor(canvas: HTMLCanvasElement, options?: VisualizerOptions);
  readonly canvas: HTMLCanvasElement;
  readonly analyser: AnalyserNode;
  baseHue: number;
  particleCount: number;
  resize(): void;
  setBaseHue(h: number): this;
  setParticles(n: number): this;
  start(): this;
  stop(): this;
  readonly running: boolean;
  readonly last: AudioFrame;
  analyze(): AudioFrame;
  dispose(): void;
}

export function resolveAnalyser(options: VisualizerOptions): AnalyserNode;
export function coverColor(img: CanvasImageSource): CoverColor;
export function createVisualizer(canvas: HTMLCanvasElement, options?: VisualizerOptions): DolbyVisualizer;
export default DolbyVisualizer;
