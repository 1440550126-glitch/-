const { parseCopy } = require('./aiParser');
const { moderateText } = require('./moderation');

const KEY = 'juling_store_v1';
const AI_USER = {
  _id: 'ai_warmup_officer',
  nickname: 'AI 暖场官',
  avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=juling-ai',
  bio: '我会在合适的时间，让一句话先亮起来。',
  follow_count: 0,
  fans_count: 520,
  post_count: 0,
  is_ai_account: true,
  created_at: 0
};
const DEMO_USER = {
  _id: 'user_demo',
  nickname: '句灵体验官',
  avatar: 'https://api.dicebear.com/7.x/thumbs/svg?seed=juling',
  bio: '正在让每一句文案拥有生命。',
  follow_count: 0,
  fans_count: 0,
  post_count: 0,
  is_ai_account: false,
  created_at: 0
};
const WARMUP_TEXTS = [
  { text: '我在等风，也在等你。', emotion: '治愈孤独', theme: '风' },
  { text: '雨停了，可我还站在原地。', emotion: '孤独', theme: '雨天' },
  { text: '今天也要像太阳一样，慢慢升起来。', emotion: '治愈', theme: '早晨' },
  { text: '饭要好好吃，生活才不会塌。', emotion: '生活感', theme: '中午' },
  { text: '猫突然出现，把我的坏心情撞飞了。', emotion: '搞笑治愈', theme: '猫咪' },
  { text: '少年往前跑，风会替你鼓掌。', emotion: '热血', theme: '校园' }
];
function clone(data) { return JSON.parse(JSON.stringify(data)); }
function now() { return Date.now(); }
function id(prefix) { return `${prefix}_${now()}_${Math.random().toString(36).slice(2, 8)}`; }
function emptyStore() {
  return { posts: [], comments: [], users: [DEMO_USER, AI_USER], likes: [], collects: [], follows: [], shares: [], ai_warmup_logs: [] };
}
function getStore() {
  try {
    const raw = wx.getStorageSync(KEY);
    return raw ? JSON.parse(raw) : emptyStore();
  } catch (err) { return emptyStore(); }
}
function saveStore(store) { wx.setStorageSync(KEY, JSON.stringify(store)); return store; }
function enrichPost(store, post) {
  const user = store.users.find((item) => item._id === post.user_id) || DEMO_USER;
  return { ...post, user, liked: store.likes.some((item) => item.post_id === post._id && item.user_id === DEMO_USER._id), collected: store.collects.some((item) => item.post_id === post._id && item.user_id === DEMO_USER._id) };
}
function seedIfNeeded() {
  const store = getStore();
  if (store.posts.length) return;
  WARMUP_TEXTS.forEach((item, index) => {
    const parsed = parseCopy({ text: item.text, emotionTag: item.emotion, theme: item.theme });
    const postId = id('post');
    parsed.animation_manifest.post_id = postId;
    store.posts.push({
      _id: postId,
      user_id: AI_USER._id,
      text: item.text,
      emotion: parsed.emotion,
      theme: item.theme,
      preview_config: parsed.preview_config,
      animation_manifest: parsed.animation_manifest,
      audio_config: { sounds: parsed.sound },
      like_count: Math.floor(Math.random() * 30) + 5,
      comment_count: index % 2,
      share_count: Math.floor(Math.random() * 5),
      collect_count: Math.floor(Math.random() * 8),
      play_count: Math.floor(Math.random() * 50) + 8,
      is_ai_post: true,
      status: 'published',
      created_at: now() - index * 3600000,
      updated_at: now() - index * 3600000
    });
  });
  store.comments.push({ _id: id('comment'), post_id: store.posts[0]._id, user_id: AI_USER._id, content: '长按一下，风会从字里吹出来。', reply_to: null, like_count: 6, status: 'published', created_at: now() });
  saveStore(store);
}
function listPosts({ sort = 'latest', userId = '' } = {}) {
  const store = getStore();
  let posts = store.posts.filter((post) => post.status === 'published');
  if (userId) posts = posts.filter((post) => post.user_id === userId);
  if (sort === 'hot') posts.sort((a, b) => score(b) - score(a)); else posts.sort((a, b) => b.created_at - a.created_at);
  return clone(posts.map((post) => enrichPost(store, post)));
}
function score(post) {
  const ageHours = Math.max(1, (now() - post.created_at) / 3600000);
  return post.like_count * 3 + post.comment_count * 5 + post.share_count * 8 + post.collect_count * 6 + (post.play_count || 0) * 4 - ageHours * 0.8;
}
function getPost(postId) {
  const store = getStore();
  const post = store.posts.find((item) => item._id === postId);
  return post ? clone(enrichPost(store, post)) : null;
}
function publishPost({ text, emotionTag = '', theme = '', user = DEMO_USER }) {
  const moderation = moderateText(text);
  if (moderation.status === 'blocked') return { ok: false, moderation };
  const parsed = parseCopy({ text, emotionTag, theme });
  const store = getStore();
  if (!store.users.some((item) => item._id === user._id)) store.users.push(user);
  const postId = id('post');
  parsed.animation_manifest.post_id = postId;
  const post = {
    _id: postId,
    user_id: user._id,
    text: String(text).trim(),
    emotion: parsed.emotion,
    theme: theme || parsed.scene,
    preview_config: parsed.preview_config,
    animation_manifest: parsed.animation_manifest,
    audio_config: { sounds: parsed.sound },
    like_count: 0,
    comment_count: 0,
    share_count: 0,
    collect_count: 0,
    play_count: 0,
    is_ai_post: !!user.is_ai_account,
    status: moderation.status === 'review' ? 'review' : 'published',
    moderation,
    created_at: now(),
    updated_at: now()
  };
  store.posts.unshift(post);
  saveStore(store);
  return { ok: post.status === 'published', post: enrichPost(store, post), moderation };
}
function toggleLike(postId, userId = DEMO_USER._id) {
  const store = getStore();
  const post = store.posts.find((item) => item._id === postId);
  if (!post) return null;
  const index = store.likes.findIndex((item) => item.post_id === postId && item.user_id === userId);
  if (index >= 0) { store.likes.splice(index, 1); post.like_count = Math.max(0, post.like_count - 1); }
  else { store.likes.push({ _id: id('like'), user_id: userId, post_id: postId, created_at: now() }); post.like_count += 1; }
  saveStore(store); return enrichPost(store, post);
}
function toggleCollect(postId, userId = DEMO_USER._id) {
  const store = getStore(); const post = store.posts.find((item) => item._id === postId); if (!post) return null;
  const index = store.collects.findIndex((item) => item.post_id === postId && item.user_id === userId);
  if (index >= 0) { store.collects.splice(index, 1); post.collect_count = Math.max(0, post.collect_count - 1); }
  else { store.collects.push({ _id: id('collect'), user_id: userId, post_id: postId, created_at: now() }); post.collect_count += 1; }
  saveStore(store); return enrichPost(store, post);
}
function addComment({ postId, content, replyTo = null, userId = DEMO_USER._id }) {
  const moderation = moderateText(content); if (moderation.status === 'blocked') return { ok: false, moderation };
  const store = getStore(); const post = store.posts.find((item) => item._id === postId); if (!post) return { ok: false };
  const comment = { _id: id('comment'), post_id: postId, user_id: userId, content: String(content).trim(), reply_to: replyTo, like_count: 0, status: moderation.status === 'review' ? 'review' : 'published', created_at: now() };
  store.comments.push(comment); post.comment_count += comment.status === 'published' ? 1 : 0; saveStore(store); return { ok: comment.status === 'published', comment, moderation };
}
function listComments(postId) {
  const store = getStore();
  return clone(store.comments.filter((item) => item.post_id === postId && item.status === 'published').map((comment) => ({ ...comment, user: store.users.find((user) => user._id === comment.user_id) || DEMO_USER })));
}
function recordShare(postId, userId = DEMO_USER._id) {
  const store = getStore(); const post = store.posts.find((item) => item._id === postId); if (!post) return null;
  store.shares.push({ _id: id('share'), user_id: userId, post_id: postId, created_at: now() }); post.share_count += 1; saveStore(store); return enrichPost(store, post);
}
function recordPlay(postId) { const store = getStore(); const post = store.posts.find((item) => item._id === postId); if (post) { post.play_count = (post.play_count || 0) + 1; saveStore(store); } }
function aiWarmupPost() {
  const picked = WARMUP_TEXTS[Math.floor(Math.random() * WARMUP_TEXTS.length)];
  const result = publishPost({ text: picked.text, emotionTag: picked.emotion, theme: picked.theme, user: AI_USER });
  const store = getStore(); if (result.post) store.ai_warmup_logs.push({ _id: id('log'), ai_user_id: AI_USER._id, post_id: result.post._id, type: 'manual_warmup', created_at: now() }); saveStore(store);
  return result;
}
module.exports = { seedIfNeeded, listPosts, getPost, publishPost, toggleLike, toggleCollect, addComment, listComments, recordShare, recordPlay, aiWarmupPost, score, DEMO_USER, AI_USER };
