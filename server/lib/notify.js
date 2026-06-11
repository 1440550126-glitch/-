// 通知中心：互动 / 系统 / AI 暖场消息
import { q } from './db.js';
import { now } from './util.js';
import { publishTo } from './hub.js';

/**
 * 写入通知并通过个人 SSE 通道实时提醒（用户在线时小铃铛立即 +1）
 */
export function notify(userId, kind, { actorId = null, postId = null, commentId = null, content = '' } = {}) {
  if (!userId || userId === actorId) return;   // 不通知自己
  // 防轰炸：同人同帖同类型 10 分钟内只记一条
  if (actorId) {
    const dup = q.get(
      'SELECT id FROM notifications WHERE user_id=? AND kind=? AND actor_id=? AND COALESCE(post_id,0)=? AND created_at > ?',
      userId, kind, actorId, postId || 0, now() - 600_000
    );
    if (dup) return;
  }
  q.run(
    'INSERT INTO notifications (user_id, kind, actor_id, post_id, comment_id, content, created_at) VALUES (?,?,?,?,?,?,?)',
    userId, kind, actorId, postId, commentId, String(content).slice(0, 120), now()
  );
  publishTo('inbox', userId, 'notify', { kind });
}

export function unreadCount(userId) {
  return q.get('SELECT COUNT(*) c FROM notifications WHERE user_id = ? AND read = 0', userId)?.c || 0;
}
