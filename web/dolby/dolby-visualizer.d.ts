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
  analyze(): AudioFrame;
  dispose(): void;
}

export function coverColor(img: CanvasImageSource): CoverColor;
export function createVisualizer(canvas: HTMLCanvasElement, options?: VisualizerOptions): DolbyVisualizer;
export default DolbyVisualizer;
