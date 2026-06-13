// 纯逻辑单元测试（无需启动服务/数据库）：推荐排序 + 陪聊兜底与安全红线
// 运行：npm test
import { scoreAndRank } from '../server/lib/recsys.js';
import { localReply, CARE_REPLY, HOTLINE, COMPANION_GREETING, COMPANION_SYSTEM } from '../server/lib/companion.js';

let pass = 0, fail = 0;
const ok = (n, c, x = '') => { if (c) { pass++; console.log('  ✅', n); } else { fail++; console.log('  ❌', n, x); } };

console.log('\n== 个性化推荐 recsys（纯函数） ==');
{
  const T = Date.now();
  const post = (id, user, emo, counts = {}, ageH = 2, topic = null) => ({
    id, user_id: user, card: JSON.stringify({ emotion: emo }), topic_id: topic,
    like_count: counts.like || 0, comment_count: counts.comment || 0, collect_count: counts.collect || 0,
    share_count: 0, play_count: counts.play || 0, created_at: T - ageH * 3600_000
  });

  // 冷启动：高互动 > 低互动，且给出理由
  let r = scoreAndRank([post(1, 10, '治愈'), post(2, 11, '难过', { like: 30, comment: 10, collect: 8 })], null, { daySeed: 1 });
  ok('冷启动按热度+新鲜：高互动排前', r[0].post.id === 2);
  ok('冷启动也给推荐理由', typeof r[0].reason === 'string' && r[0].reason.length > 0);

  // 情绪个性化
  const profEmo = { emotions: { 治愈: 1 }, authors: {}, topics: {}, total: 30, dismissedPosts: new Set(), dismissedAuthors: new Map() };
  r = scoreAndRank([post(1, 10, '难过', { like: 5 }), post(2, 11, '治愈', { like: 5 })], profEmo, { daySeed: 1 });
  ok('命中情绪→治愈帖排第一', r[0].post.id === 2 && r[0].reason.includes('治愈'));

  // 作者个性化
  const profAuth = { emotions: {}, authors: { 99: 1 }, topics: {}, total: 30, dismissedPosts: new Set(), dismissedAuthors: new Map() };
  r = scoreAndRank([post(1, 10, '平静', { like: 5 }), post(2, 99, '平静', { like: 5 })], profAuth, { daySeed: 1 });
  ok('命中作者→该作者帖排第一', r[0].post.id === 2 && r[0].reason.includes('常看'));

  // 不感兴趣剔除
  r = scoreAndRank([post(1, 10, '治愈'), post(2, 11, '治愈')], { emotions: {}, authors: {}, topics: {}, total: 30, dismissedPosts: new Set([2]), dismissedAuthors: new Map() }, { daySeed: 1 });
  ok('不感兴趣帖被剔除', !r.some((x) => x.post.id === 2));

  // 不推自己的帖
  r = scoreAndRank([post(1, 5, '治愈', { like: 99 }), post(2, 11, '治愈', { like: 1 })], null, { viewerId: 5, daySeed: 1 });
  ok('自己的帖被压到最后', r[r.length - 1].post.id === 1);

  // 多样性：同作者不霸屏
  const pool = [];
  for (let i = 1; i <= 6; i++) pool.push(post(i, 7, '治愈', { like: 50 - i }));
  pool.push(post(100, 8, '治愈', { like: 10 }));
  r = scoreAndRank(pool, null, { daySeed: 1 });
  ok('多样性：前排不被单一作者霸屏', new Set(r.slice(0, 3).map((x) => x.post.user_id)).size >= 2);
}

console.log('\n== AI 陪聊 companion（纯函数 + 安全红线） ==');
{
  for (const c of ['压力好大焦虑睡不着', '我好难过撑不住了', '一个人好孤独', '好想念他分手了', '今天上岸啦太开心', '随便聊聊']) {
    ok(`兜底回应非空且像样：${c.slice(0, 6)}…`, typeof localReply(c) === 'string' && localReply(c).length >= 12);
  }
  ok('兜底确定性（同输入同输出）', localReply('我好焦虑') === localReply('我好焦虑'));
  ok('不同情绪不同回应', localReply('我好开心') !== localReply('我好难过'));
  ok('关怀响应含援助热线 12356', CARE_REPLY.includes('12356') && HOTLINE.includes('12356'));
  ok('开场白非空', COMPANION_GREETING.length > 0);
  ok('系统提示含安全红线（自伤/热线/不诊断）', COMPANION_SYSTEM.includes('12356') && COMPANION_SYSTEM.includes('自伤') && COMPANION_SYSTEM.includes('诊断'));
}

console.log(`\n========== 单测结果：${pass} 通过 / ${fail} 失败 ==========\n`);
process.exit(fail ? 1 : 0);
