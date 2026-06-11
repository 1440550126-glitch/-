const db = require('../../utils/db');
Page({
  data: { id: '', post: null, comments: [], commentText: '', replyTo: null, replyHint: '', objectText: '', soundText: '' },
  onLoad(options) { this.setData({ id: options.id }); this.load(); },
  load() {
    const post = db.getPost(this.data.id); if (!post) { wx.showToast({ title: '内容不存在', icon: 'none' }); return; }
    const comments = db.listComments(post._id);
    this.setData({ post, comments, objectText: (post.animation_manifest.elements || []).map((item) => item.type).join('、'), soundText: (post.audio_config.sounds || []).join('、') });
  },
  likePost(e) { db.toggleLike(e.detail.postId); this.load(); },
  collectPost(e) { db.toggleCollect(e.detail.postId); this.load(); },
  sharePost(e) { db.recordShare(e.detail.postId); wx.showToast({ title: '已记录分享' }); this.load(); },
  recordPlay(e) { db.recordPlay(e.detail.postId); this.load(); },
  onComment(e) { this.setData({ commentText: e.detail.value }); },
  prepareReply(e) { this.setData({ replyTo: e.detail.id, replyHint: `回复 ${e.detail.name}` }); },
  sendComment() {
    const result = db.addComment({ postId: this.data.post._id, content: this.data.commentText, replyTo: this.data.replyTo });
    if (!result.ok) { wx.showModal({ title: '评论未发布', content: result.moderation ? result.moderation.reason : '请重试', showCancel: false }); return; }
    wx.showToast({ title: '评论已点亮' }); this.setData({ commentText: '', replyTo: null, replyHint: '' }); this.load();
  }
});
