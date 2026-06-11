const { seedIfNeeded } = require('./utils/db');

App({
  globalData: {
    user: {
      _id: 'user_demo',
      nickname: '句灵体验官',
      avatar: 'https://api.dicebear.com/7.x/thumbs/svg?seed=juling',
      bio: '正在让每一句文案拥有生命。',
      is_ai_account: false
    }
  },
  onLaunch() {
    if (wx.cloud) {
      try {
        wx.cloud.init({ traceUser: true });
      } catch (err) {
        console.warn('cloud init skipped', err);
      }
    }
    seedIfNeeded();
  }
});
