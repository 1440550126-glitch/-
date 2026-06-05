const db = require('../../utils/db');
Page({
  data: { posts: [], sort: 'latest' },
  onShow() { this.load(); },
  onPullDownRefresh() { this.load(); wx.stopPullDownRefresh(); },
  load() { this.setData({ posts: db.listPosts({ sort: this.data.sort }) }); },
  switchLatest() { this.setData({ sort: 'latest' }, () => this.load()); },
  switchHot() { this.setData({ sort: 'hot' }, () => this.load()); },
  likePost(e) { db.toggleLike(e.detail.postId); this.load(); },
  collectPost(e) { db.toggleCollect(e.detail.postId); this.load(); },
  sharePost(e) { db.recordShare(e.detail.postId); wx.showToast({ title: '已记录分享' }); this.load(); },
  recordPlay(e) { db.recordPlay(e.detail.postId); this.load(); },
  aiWarmup() { const result = db.aiWarmupPost(); wx.showToast({ title: result.ok ? 'AI 已发文' : '暖场失败' }); this.load(); }
});
