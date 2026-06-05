const SOUND_MAP = {
  soft_start: '/assets/sounds/soft_start.mp3', text_glow: '/assets/sounds/text_glow.mp3', wind_soft: '/assets/sounds/wind_soft.mp3', rain_soft: '/assets/sounds/rain_soft.mp3', heartbeat_soft: '/assets/sounds/heartbeat_soft.mp3', line_draw: '/assets/sounds/line_draw.mp3', light_pop: '/assets/sounds/light_pop.mp3', glass_break_soft: '/assets/sounds/glass_break_soft.mp3', footstep_soft: '/assets/sounds/footstep_soft.mp3', ocean_soft: '/assets/sounds/ocean_soft.mp3', cat_meow_soft: '/assets/sounds/cat_meow_soft.mp3', city_soft: '/assets/sounds/city_soft.mp3', sigh_soft: '/assets/sounds/sigh_soft.mp3'
};
class AudioEngine {
  constructor() { this.pool = {}; this.triggered = {}; }
  preload(names = []) { names.forEach((name) => this.get(name)); }
  get(name) { if (!name || this.pool[name]) return this.pool[name]; if (!wx.createInnerAudioContext) return null; const audio = wx.createInnerAudioContext(); audio.src = SOUND_MAP[name] || `/assets/sounds/${name}.mp3`; audio.obeyMuteSwitch = false; this.pool[name] = audio; return audio; }
  play(name, { loop = false, volume = 0.75 } = {}) { const audio = this.get(name); if (!audio) return; audio.loop = loop; audio.volume = volume; try { audio.stop(); audio.play(); } catch (err) { console.warn('audio play failed', name, err); } }
  fadeOut(name, duration = 500) { const audio = this.pool[name]; if (!audio) return; const start = audio.volume || 0.6; const steps = 8; let i = 0; const timer = setInterval(() => { i += 1; audio.volume = Math.max(0, start * (1 - i / steps)); if (i >= steps) { clearInterval(timer); audio.stop(); } }, duration / steps); }
  syncTimeline(timeline = [], seconds = 0) { timeline.forEach((item) => { if (!item.sound) return; const key = `${item.time}_${item.sound}`; if (!this.triggered[key] && seconds >= item.time) { this.triggered[key] = true; this.play(item.sound, { loop: item.duration > 2 && item.sound.includes('soft'), volume: 0.62 }); } }); }
  reset() { Object.keys(this.pool).forEach((name) => this.fadeOut(name, 220)); this.triggered = {}; }
}
module.exports = { AudioEngine, SOUND_MAP };
