const { parseCopy } = require('../../utils/aiParser');
const { moderateText } = require('../../utils/moderation');
const db = require('../../utils/db');
const app = getApp();
Page({
  data: { text: '', emotionTag: '治愈', theme: '极简风', emotions: ['治愈','孤独','恋爱','搞笑','热血','emo','松弛感'], themes: ['极简风','夜晚','海边','城市','校园','雨天','猫咪','古风','动漫风'], previewPost: null },
  onText(e) { this.setData({ text: e.detail.value }); },
  pickEmotion(e) { this.setData({ emotionTag: e.currentTarget.dataset.value }); },
  pickTheme(e) { this.setData({ theme: e.currentTarget.dataset.value }); },
  generate() {
    const moderation = moderateText(this.data.text);
    if (moderation.status === 'blocked') { wx.showModal({ title: '无法生成', content: moderation.reason, showCancel: false }); return; }
    if (moderation.care) wx.showModal({ title: '给你一个拥抱', content: '这类内容不会被唯美化扩散。如果你正处在危险里，请马上联系身边的人或当地紧急帮助。', showCancel: false });
    const parsed = parseCopy({ text: this.data.text, emotionTag: this.data.emotionTag, theme: this.data.theme });
    const previewPost = { _id: 'preview', user: app.globalData.user, user_id: app.globalData.user._id, text: this.data.text, emotion: parsed.emotion, theme: this.data.theme, preview_config: parsed.preview_config, animation_manifest: parsed.animation_manifest, like_count:0, comment_count:0, share_count:0, collect_count:0 };
    this.setData({ previewPost });
  },
  publish() {
    const result = db.publishPost({ text: this.data.text, emotionTag: this.data.emotionTag, theme: this.data.theme, user: app.globalData.user });
    if (!result.ok) { wx.showModal({ title: result.moderation.care ? '需要人工审核' : '发布失败', content: result.moderation.reason, showCancel: false }); return; }
    wx.showToast({ title: '发布成功' }); this.setData({ text: '', previewPost: null }); wx.switchTab({ url: '/pages/index/index' });
  }
});
