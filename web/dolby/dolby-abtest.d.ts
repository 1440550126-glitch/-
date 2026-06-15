// 类型定义 · dolby-abtest
export type ABSlot = 'A' | 'B';

export interface ABResult {
  round: number;
  picked: ABSlot;
  enhancedSlot: ABSlot;
  pickedEnhanced: boolean;
}

export interface ABStats {
  rounds: number;
  preferEnhanced: number;
  /** 偏好增强率 0..1 */
  rate: number;
}

export interface ABTestOptions {
  random?: () => number;
}

/** 仅需具备 setEnabled 的对象（DolbyAudio 满足） */
export interface ABEngine {
  setEnabled(on: boolean): unknown;
}

export class DolbyABTest {
  constructor(dolby: ABEngine, options?: ABTestOptions);
  rounds: number;
  preferEnhanced: number;
  reset(): this;
  newRound(forceSlot?: ABSlot): this;
  audition(slot: ABSlot): this;
  choose(slot: ABSlot): ABResult;
  readonly enhancedSlot: ABSlot | null;
  readonly current: ABSlot | null;
  readonly stats: ABStats;
}

export function createABTest(dolby: ABEngine, options?: ABTestOptions): DolbyABTest;
export default DolbyABTest;
