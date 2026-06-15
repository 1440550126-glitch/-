// 类型定义 · dolby-visualizer-gl
import type { VisualizerOptions, AudioFrame, DolbyVisualizer } from './dolby-visualizer';

export interface VisualizerGLOptions extends VisualizerOptions {
  /** 'webgl' 强制 WebGL（失败抛错）/ 'canvas' 强制 Canvas2D / 默认自动回退 */
  renderer?: 'webgl' | 'canvas';
  /** 渲染分辨率倍数，默认 min(dpr, 1.5) */
  scale?: number;
}

export class DolbyVisualizerGL {
  constructor(canvas: HTMLCanvasElement, options?: VisualizerGLOptions);
  readonly canvas: HTMLCanvasElement;
  readonly analyser: AnalyserNode;
  readonly renderer: 'webgl';
  baseHue: number;
  scale: number;
  resize(): void;
  setBaseHue(h: number): this;
  setParticles(n?: number): this;
  analyze(): AudioFrame;
  start(): this;
  stop(): this;
  readonly running: boolean;
  dispose(): void;
}

/** 优先 WebGL，失败自动回退到 Canvas2D 的 DolbyVisualizer */
export function createVisualizer(canvas: HTMLCanvasElement, options?: VisualizerGLOptions): DolbyVisualizerGL | DolbyVisualizer;
export default DolbyVisualizerGL;
