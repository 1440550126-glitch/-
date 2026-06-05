const { renderManifest } = require('../../utils/motionEngine');
const { AudioEngine } = require('../../utils/audioEngine');
Component({
  properties: { manifest: { type: Object, value: null }, autoFinish: { type: Boolean, value: true } },
  data: { playing: false },
  lifetimes: { detached() { this.stop(true); } },
  methods: {
    initCanvas(cb) {
      const query = this.createSelectorQuery();
      query.select('#livingCanvas').fields({ node: true, size: true }).exec((res) => {
        const canvas = res && res[0] && res[0].node; if (!canvas) return;
        const dpr = wx.getSystemInfoSync().pixelRatio || 1; canvas.width = res[0].width * dpr; canvas.height = res[0].height * dpr;
        const ctx = canvas.getContext('2d'); ctx.scale(dpr, dpr); this.canvas = canvas; this.ctx = ctx; this.width = res[0].width; this.height = res[0].height; cb && cb();
      });
    },
    play() {
      const manifest = this.properties.manifest; if (!manifest) return;
      this.stop(false); this.setData({ playing: true }); this.audio = this.audio || new AudioEngine(); this.audio.preload((manifest.timeline || []).map((item) => item.sound).filter(Boolean));
      this.triggerEvent('playstart', { postId: manifest.post_id });
      this.initCanvas(() => { this.startedAt = Date.now(); const tick = () => { const seconds = (Date.now() - this.startedAt) / 1000; renderManifest(this.ctx, manifest, seconds, this.width, this.height); this.audio.syncTimeline(manifest.timeline, seconds); if (seconds < (manifest.duration || 6)) this.raf = this.canvas.requestAnimationFrame(tick); else this.finish(); }; tick(); });
    },
    finish() { this.audio && this.audio.reset(); this.setData({ playing: false }); this.triggerEvent('playend'); },
    stop(immediate = false) { if (this.canvas && this.raf) this.canvas.cancelAnimationFrame(this.raf); this.raf = null; if (immediate || !this.properties.autoFinish) { this.audio && this.audio.reset(); this.setData({ playing: false }); } }
  }
});
