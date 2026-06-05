Component({
  properties: { post: { type: Object, value: {} } },
  data: { pressing: false },
  methods: {
    noop() {},
    touchStart() { this.setData({ pressing: true }); },
    touchEnd() { setTimeout(() => this.setData({ pressing: false }), 160); },
    startLiving() { this.selectComponent('#anim').play(); },
    onPlayStart(e) { this.triggerEvent('play', e.detail); },
    like() { this.triggerEvent('like', { postId: this.properties.post._id }); },
    collect() { this.triggerEvent('collect', { postId: this.properties.post._id }); },
    share() { this.triggerEvent('share', { postId: this.properties.post._id }); },
    openDetail() { wx.navigateTo({ url: `/pages/detail/detail?id=${this.properties.post._id}` }); }
  }
});
