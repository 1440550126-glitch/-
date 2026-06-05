const db = require('../../utils/db');
const app = getApp();
Page({
  data: { user: {}, posts: [], collectCount: 0 },
  onShow() { this.load(); },
  load() { const user = app.globalData.user; const posts = db.listPosts({ userId: user._id }); this.setData({ user, posts, collectCount: posts.filter((item) => item.collected).length }); },
  likePost(e) { db.toggleLike(e.detail.postId); this.load(); },
  collectPost(e) { db.toggleCollect(e.detail.postId); this.load(); },
  sharePost(e) { db.recordShare(e.detail.postId); wx.showToast({ title: '已记录分享' }); this.load(); },
  recordPlay(e) { db.recordPlay(e.detail.postId); this.load(); }
});
