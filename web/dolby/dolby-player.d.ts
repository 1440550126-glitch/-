// 类型定义 · dolby-player
import type { DolbyAudio, DolbyOptions, SpatialMode, DolbyState } from './dolby-audio';

export type RepeatMode = 'off' | 'one' | 'all';

export interface Track {
  src: string;
  title?: string;
  artist?: string;
  cover?: string;
  [key: string]: unknown;
}
export type TrackInput = string | Track;

export interface DolbyPlayerOptions {
  audio?: HTMLMediaElement;
  dolby?: DolbyAudio | DolbyOptions;
  tracks?: TrackInput[];
  repeat?: RepeatMode;
  shuffle?: boolean;
  volume?: number;
  preload?: '' | 'none' | 'metadata' | 'auto';
  crossOrigin?: string;
  autoplayNext?: boolean;
  autoload?: boolean;
}

export interface PlayerState {
  index: number;
  playing: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  repeat: RepeatMode;
  shuffle: boolean;
  track: TrackInput | null;
  dolby: DolbyState;
}

export type PlayerEvent =
  | 'track' | 'play' | 'pause' | 'ended' | 'time' | 'loaded' | 'error' | 'volume' | 'playlist';

export class DolbyPlayer {
  constructor(options?: DolbyPlayerOptions);

  readonly audio: HTMLMediaElement;
  readonly dolby: DolbyAudio;
  tracks: TrackInput[];
  index: number;
  repeat: RepeatMode;
  shuffle: boolean;

  on(ev: PlayerEvent, fn: (...args: any[]) => void): this;
  off(ev: PlayerEvent, fn: (...args: any[]) => void): this;
  once(ev: PlayerEvent, fn: (...args: any[]) => void): this;

  setPlaylist(tracks: TrackInput[], opts?: { autoload?: boolean }): this;
  add(track: TrackInput): this;
  readonly current: TrackInput | null;
  load(index: number, autoplay?: boolean): this;

  play(): Promise<void>;
  pause(): this;
  toggle(): Promise<void>;
  stop(): this;
  seek(sec: number): this;
  setVolume(v: number): this;
  readonly volume: number;
  readonly playing: boolean;
  readonly currentTime: number;
  readonly duration: number;

  next(autoplay?: boolean): this;
  prev(autoplay?: boolean): this;
  setRepeat(mode: RepeatMode): this;
  setShuffle(on: boolean): this;

  setPreset(p: string | object): this;
  setIntensity(v: number): this;
  setEnabled(on: boolean): this;
  setSpatialMode(m: SpatialMode): this;

  readonly state: PlayerState;
  dispose(opts?: { closeContext?: boolean }): void;
}

export function createPlayer(options?: DolbyPlayerOptions): DolbyPlayer;
export default DolbyPlayer;
