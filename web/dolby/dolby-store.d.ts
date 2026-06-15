// 类型定义 · dolby-store（可选偏好持久化助手）
import type { DolbyAudio, SpatialMode } from './dolby-audio';

export interface DolbyPrefs {
  enabled: boolean;
  preset: string;
  intensity: number;
  spatialMode: SpatialMode;
  multiband: boolean;
  loudnessMatch: boolean;
}

export const DEFAULT_PREFS: DolbyPrefs;
export function loadPrefs(key?: string): DolbyPrefs;
export function savePrefs(prefs: Partial<DolbyPrefs>, key?: string): boolean;
export function snapshot(dolby: DolbyAudio): DolbyPrefs;
export function applyPrefs(dolby: DolbyAudio, prefs?: DolbyPrefs, opts?: { instant?: boolean }): DolbyAudio;
export function autosave(dolby: DolbyAudio, key?: string, delay?: number): DolbyAudio;
