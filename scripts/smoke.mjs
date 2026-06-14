// 全链路冒烟测试：账号 → 社交 → 审核 → 会员/皮肤/额度 → 动画 → 后台 → 完整一局谁是卧底
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = 3199;
const BASE = `http://localhost:${PORT}`;
const DB = `/tmp/jvling-smoke-${Date.now()}.sqlite`;

let passed = 0, failed = 0;
const ok = (name, cond, extra = '') => {
  if (cond) { passed++; console.log(`  ✅ ${name}`); }
  else { failed++; console.log(`  ❌ ${name} ${extra}`); }
};

async function api(method, url, { token, body } = {}) {
  const res = await fetch(BASE + url, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, ...json };
}

// 极简 SSE 客户端
function sse(url, token) {
  const events = [];
  const waiters = [];
  const ctrl = new AbortController();
  const push = (ev) => {
    events.push(ev);
    for (const w of [...waiters]) {
      if (w.match(ev)) { waiters.splice(waiters.indexOf(w), 1); clearTimeout(w.timer); w.resolve(ev); }
    }
  };
  (async () => {
    try {
      const res = await fetch(BASE + url + (url.includes('?') ? '&' : '?') + 'token=' + token, { signal: ctrl.signal });
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const chunk = buf.slice(0, idx); buf = buf.slice(idx + 2);
          let event = 'message', data = '';
          for (const line of chunk.split('\n')) {
            if (line.startsWith('event: ')) event = line.slice(7);
            if (line.startsWith('data: ')) data += line.slice(6);
          }
          if (data) { try { push({ event, data: JSON.parse(data) }); } catch { /* skip */ } }
        }
      }
    } catch { /* aborted */ }
  })();
  return {
    events,
    wait(match, timeoutMs = 15000, desc = '') {
      const found = events.find(match);
      if (found) return Promise.resolve(found);
      return new Promise((resolve, reject) => {
        const w = { match, resolve, timer: setTimeout(() => { waiters.splice(waiters.indexOf(w), 1); reject(new Error('SSE 超时: ' + desc)); }, timeoutMs) };
        waiters.push(w);
      });
    },
    close: () => ctrl.abort()
  };
}

const server = spawn('node', ['--disable-warning=ExperimentalWarning', path.join(__dirname, '..', 'server', 'index.js')], {
  env: { ...process.env, PORT: String(PORT), DB_PATH: DB, WARMUP_AUTOSTART: '0', TRIGGER_AUTOSTART: '0', LLM_PROVIDER: 'none' },
  stdio: ['ignore', 'pipe', 'inherit']
});
server.stdout.on('data', () => {});

try {
  // 等服务起来
  for (let i = 0; i < 40; i++) {
    try { const r = await fetch(BASE + '/api/health'); if (r.ok) break; } catch { /* retry */ }
    await new Promise((r) => setTimeout(r, 250));
  }

  console.log('\n== 基础 ==');
  const health = await api('GET', '/api/health');
  ok('health', health.ok && health.data.status === 'ok');
  const boot = await api('GET', '/api/bootstrap');
  ok('bootstrap 含头像与会员方案', boot.data.avatars.length === 12 && boot.data.member_plans.length === 3);

  console.log('\n== 账号 ==');
  const reg = await api('POST', '/api/auth/register', { body: { username: 'xiaoming', password: 'pass123', nickname: '小明同学' } });
  ok('注册', reg.ok, JSON.stringify(reg));
  const u1 = reg.data;
  const login = await api('POST', '/api/auth/login', { body: { username: 'xiaoming', password: 'pass123' } });
  ok('登录', login.ok);
  const badLogin = await api('POST', '/api/auth/login', { body: { username: 'xiaoming', password: 'wrong' } });
  ok('错误密码被拒', !badLogin.ok);
  const guests = [];
  for (let i = 0; i < 3; i++) guests.push((await api('POST', '/api/auth/guest', { body: {} })).data);
  ok('游客登录×3', guests.every((g) => g.token));
  const admin = (await api('POST', '/api/auth/login', { body: { username: 'admin', password: 'jvling-admin-2026' } })).data;
  ok('管理员登录', admin?.user?.role === 'admin');
  const patch = await api('PATCH', '/api/me', { token: u1.token, body: { bio: '热爱写句子的人', avatar: 'blob_3', settings: { no_ai_warmup: false } } });
  ok('编辑资料', patch.ok && patch.data.bio === '热爱写句子的人');

  console.log('\n== 文案社交 ==');
  const prev = await api('POST', '/api/ai/preview', { token: u1.token, body: { content: '我在等风，也在等你。' } });
  ok('发布前预览卡', prev.ok && prev.data.card.bg.length === 2);
  const p1 = await api('POST', '/api/posts', { token: u1.token, body: { content: '我在等风，也在等你。' } });
  ok('发布文案', p1.ok && p1.data.post.card.ai_label === 'AI 辅助生成', JSON.stringify(p1));
  const post1 = p1.data.post;
  const blockPost = await api('POST', '/api/posts', { token: u1.token, body: { content: '来玩网赌，稳赚不赔' } });
  ok('硬违规内容被拦截', !blockPost.ok);
  const sad = await api('POST', '/api/posts', { token: u1.token, body: { content: '最近真的不想活了' } });
  ok('自伤内容进入人工审核+关怀语', sad.ok && sad.data.post.status === 'pending' && sad.data.care === true, JSON.stringify(sad.data?.notice));
  const feed = await api('GET', '/api/posts?tab=new', { token: guests[0].token });
  ok('信息流含种子内容与新帖', feed.ok && feed.data.items.length >= 5);
  ok('信息流不含待审帖', !feed.data.items.some((p) => p.id === sad.data.post.id));
  ok('AI 暖场帖有标识', feed.data.items.some((p) => p.is_ai && p.ai_label));
  const like = await api('POST', `/api/posts/${post1.id}/like`, { token: guests[0].token });
  ok('点赞', like.ok && like.data.like_count === 1);
  const unlike = await api('DELETE', `/api/posts/${post1.id}/like`, { token: guests[0].token });
  ok('取消点赞', unlike.ok && unlike.data.like_count === 0);
  await api('POST', `/api/posts/${post1.id}/like`, { token: guests[0].token });
  const col = await api('POST', `/api/posts/${post1.id}/collect`, { token: guests[0].token });
  ok('收藏', col.ok && col.data.collect_count === 1);
  const c1 = await api('POST', `/api/posts/${post1.id}/comments`, { token: guests[0].token, body: { content: '这句也太温柔了吧' } });
  ok('评论', c1.ok);
  const c2 = await api('POST', `/api/posts/${post1.id}/comments`, { token: u1.token, body: { content: '谢谢你喜欢～', parent_id: c1.data.comment.id } });
  ok('回复评论', c2.ok && c2.data.comment.parent_id === c1.data.comment.id);
  const clist = await api('GET', `/api/posts/${post1.id}/comments`);
  ok('评论树（楼中楼）', clist.data.items[0]?.replies?.length === 1);
  const share = await api('POST', `/api/posts/${post1.id}/share`, { token: guests[0].token });
  ok('分享文案与计数', share.ok && share.data.share_text.includes('句灵'));
  const follow = await api('POST', `/api/users/${u1.user.id}/follow`, { token: guests[0].token });
  ok('关注', follow.ok);
  const ffeed = await api('GET', '/api/posts?tab=follow', { token: guests[0].token });
  ok('关注流', ffeed.data.items.some((p) => p.id === post1.id));
  const hot = await api('GET', '/api/posts?tab=hot');
  ok('热门榜', hot.ok && hot.data.items.length > 0);
  const blockU = await api('POST', `/api/users/${guests[1].user.id}/block`, { token: u1.token });
  ok('拉黑用户', blockU.ok);
  const topic = await api('GET', '/api/ai/topic');
  ok('今日话题（AI标识）', topic.ok && topic.data.topic.ai_label === 'AI 生成话题');

  console.log('\n== 文字变动画（核心卖点） ==');
  const m1 = await api('POST', `/api/posts/${post1.id}/manifest`, { token: guests[0].token, body: { style: 'ink' } });
  ok('免费用户生成清墨动画', m1.ok && m1.data.manifest.v === 2, JSON.stringify(m1));
  ok('Manifest 含情绪/人物/时间轴/声音', !!(m1.data.manifest.emotion && m1.data.manifest.actors.length && m1.data.manifest.timeline.length && m1.data.manifest.soundscape));
  ok('「等风」文案出现风元素与等待行为', JSON.stringify(m1.data.manifest).includes('windline') && m1.data.manifest.actors.some((a) => a.behavior === 'wait'));
  const mDeny = await api('POST', `/api/posts/${post1.id}/manifest`, { token: guests[0].token, body: { style: 'sakura' } });
  ok('非会员选会员风格被拦', !mDeny.ok && mDeny.need_member === true);
  await api('POST', `/api/posts/${post1.id}/manifest`, { token: guests[0].token, body: { style: 'ink' } });
  await api('POST', `/api/posts/${post1.id}/manifest`, { token: guests[0].token, body: { style: 'ink' } });
  const mQuota = await api('POST', `/api/posts/${post1.id}/manifest`, { token: guests[0].token, body: { style: 'ink' } });
  ok('免费配额 3 次/日用尽后拦截', !mQuota.ok && mQuota.quota_exceeded === true, JSON.stringify(mQuota));
  await api('POST', `/api/posts/${post1.id}/play`, { token: guests[0].token });

  console.log('\n== 商业化（沙盒支付） ==');
  const ord = await api('POST', '/api/shop/orders', { token: guests[0].token, body: { kind: 'member', item_id: 'm1' } });
  ok('创建会员订单 ¥9.9', ord.ok && ord.data.order.amount_fen === 990);
  const pay = await api('POST', `/api/shop/orders/${ord.data.order.id}/pay`, { token: guests[0].token });
  ok('沙盒支付成功→成为会员', pay.ok && pay.data.me.is_member === true);
  const mMember = await api('POST', `/api/posts/${post1.id}/manifest`, { token: guests[0].token, body: { style: 'sakura' } });
  ok('会员解锁樱粉风格', mMember.ok && mMember.data.manifest.style === 'sakura', JSON.stringify(mMember).slice(0, 200));
  const mPrem = await api('POST', `/api/posts/${post1.id}/manifest`, { token: guests[0].token, body: { style: 'aurora' } });
  ok('高级风格无额度被拦', !mPrem.ok && mPrem.need_credits === true);
  const ordC = await api('POST', '/api/shop/orders', { token: guests[0].token, body: { kind: 'credits', item_id: 'c60' } });
  await api('POST', `/api/shop/orders/${ordC.data.order.id}/pay`, { token: guests[0].token });
  const mPrem2 = await api('POST', `/api/posts/${post1.id}/manifest`, { token: guests[0].token, body: { style: 'aurora' } });
  ok('购买额度后生成高级风格（会员8折扣点）', mPrem2.ok && mPrem2.data.charged === 8 && mPrem2.data.credits === 52, JSON.stringify(mPrem2).slice(0, 150));
  const cat = await api('GET', '/api/shop/catalog', { token: guests[0].token });
  const skin = cat.data.skins.find((s) => s.id === 'cf_sakura');
  ok('商城目录（皮肤含公平声明）', !!skin && cat.data.fair_play.includes('公平'));
  const ordS = await api('POST', '/api/shop/orders', { token: guests[0].token, body: { kind: 'skin', item_id: 'cf_sakura' } });
  await api('POST', `/api/shop/orders/${ordS.data.order.id}/pay`, { token: guests[0].token });
  const equip = await api('POST', '/api/me/equip', { token: guests[0].token, body: { type: 'card_frame', skin_id: 'cf_sakura' } });
  ok('购买并装备皮肤', equip.ok && equip.data.equipped.card_frame === 'cf_sakura');
  const equipDeny = await api('POST', '/api/me/equip', { token: u1.token, body: { type: 'card_frame', skin_id: 'cf_sakura' } });
  ok('未拥有的皮肤不能装备', !equipDeny.ok);
  await api('PATCH', '/api/me', { token: u1.token, body: { settings: { teen_mode: true } } });
  const teenOrd = await api('POST', '/api/shop/orders', { token: u1.token, body: { kind: 'member', item_id: 'm1' } });
  ok('青少年模式禁止消费', !teenOrd.ok);
  await api('PATCH', '/api/me', { token: u1.token, body: { settings: { teen_mode: false } } });

  console.log('\n== 举报与后台 ==');
  const rep = await api('POST', '/api/reports', { token: guests[0].token, body: { target_type: 'post', target_id: post1.id, reason: '其他', detail: '测试举报' } });
  ok('提交举报', rep.ok);
  const stats = await api('GET', '/api/admin/stats', { token: admin.token });
  ok('后台统计', stats.ok && stats.data.users.total >= 4 && Number(stats.data.revenue.total_yuan) > 0, JSON.stringify(stats.data?.revenue));
  ok('后台成本统计存在', stats.data.ai.today_calls > 0);
  const noAdmin = await api('GET', '/api/admin/stats', { token: u1.token });
  ok('普通用户无后台权限', noAdmin.status === 403);
  const reports = await api('GET', '/api/admin/reports?status=open', { token: admin.token });
  ok('后台看到举报+内容快照', reports.data.items.length === 1 && !!reports.data.items[0].snapshot);
  const handle = await api('POST', `/api/admin/reports/${reports.data.items[0].id}/handle`, { token: admin.token, body: { action: 'dismiss', note: '测试' } });
  ok('处理举报', handle.ok);
  const pend = await api('GET', '/api/admin/posts?status=pending', { token: admin.token });
  ok('待审队列含自伤关怀帖', pend.data.items.some((p) => p.id === sad.data.post.id));
  const approve = await api('POST', `/api/admin/posts/${sad.data.post.id}/action`, { token: admin.token, body: { action: 'reject', reason: '人工评估' } });
  ok('人工审核操作', approve.ok);
  const ban = await api('POST', `/api/admin/users/${guests[2].user.id}/ban`, { token: admin.token, body: { days: 1, reason: '测试封禁' } });
  ok('封禁用户', ban.ok);
  const bannedPost = await api('POST', '/api/posts', { token: guests[2].token, body: { content: '我还能发吗' } });
  ok('封禁用户无法发布', bannedPost.status === 403);
  await api('POST', `/api/admin/users/${guests[2].user.id}/unban`, { token: admin.token });
  const wcfg = await api('PUT', '/api/admin/warmup', { token: admin.token, body: { posts_per_day: 20 } });
  ok('暖场频率配置', wcfg.ok && wcfg.data.config.posts_per_day === 20);
  const wTrig = await api('POST', '/api/admin/warmup/trigger', { token: admin.token, body: {} });
  ok('手动触发暖场发帖', wTrig.ok && wTrig.data.post_id > 0);
  const wOff = await api('PUT', '/api/admin/warmup', { token: admin.token, body: { enabled: false } });
  ok('一键关闭 AI 暖场', wOff.ok && wOff.data.config.enabled === false);
  await api('PUT', '/api/admin/warmup', { token: admin.token, body: { enabled: true } });
  const usage = await api('GET', '/api/admin/ai-usage', { token: admin.token });
  ok('AI 成本日报', usage.ok && usage.data.daily.length === 7);
  const sw = await api('POST', '/api/admin/sensitive-words', { token: admin.token, body: { word: '测试违禁词xyz', category: 'block' } });
  ok('新增敏感词', sw.ok);
  const swPost = await api('POST', '/api/posts', { token: u1.token, body: { content: '包含测试违禁词xyz的内容' } });
  ok('新敏感词即刻生效', !swPost.ok);

  console.log('\n== 谁是卧底（4 真人完整一局） ==');
  const players = [u1, ...guests];   // 4 人
  const create = await api('POST', '/api/rooms', { token: u1.token, body: { name: '冒烟测试房', max_players: 6, allow_bots: false } });
  ok('创建房间', create.ok, JSON.stringify(create));
  const roomId = create.data.room.id;
  const streams = players.map((p) => sse(`/api/rooms/${roomId}/events`, p.token));
  for (const g of guests) {
    const j = await api('POST', `/api/rooms/${roomId}/join`, { token: g.token });
    if (!j.ok) console.log('join fail', JSON.stringify(j));
  }
  const lobby = sse('/api/lobby/events', u1.token);
  await lobby.wait((e) => e.event === 'rooms', 5000, '大厅房间列表');
  ok('大厅 SSE 推送房间列表', true);
  for (const p of players) await api('POST', `/api/rooms/${roomId}/ready`, { token: p.token, body: { ready: true } });
  const start = await api('POST', `/api/rooms/${roomId}/start`, { token: u1.token });
  ok('开始游戏', start.ok, JSON.stringify(start));

  // 每人通过私有 SSE 拿到自己的词
  const words = [];
  for (let i = 0; i < 4; i++) {
    const ev = await streams[i].wait((e) => e.event === 'word', 8000, '发词');
    words.push(ev.data.word);
  }
  ok('私发词语（公共流不泄露）', words.every(Boolean) && new Set(words).size === 2, words.join(','));
  const counts = {};
  for (const w of words) counts[w] = (counts[w] || 0) + 1;
  const spyWord = Object.entries(counts).find(([, c]) => c === 1)[0];
  const spyIdx = words.indexOf(spyWord);
  ok('身份分配：1 卧底 3 平民', spyIdx >= 0);

  // 描述阶段：按回合轮流发言（卧底不能说出自己的词的校验）
  const selfWordTry = await (async () => {
    const st = await api('GET', `/api/rooms/${roomId}`, { token: players[0].token });
    const turn = st.data.room.turn_seat;
    const who = st.data.room.players.find((x) => x.seat === turn);
    const idx = players.findIndex((p) => p.user.id === who.user_id);
    return api('POST', `/api/rooms/${roomId}/speak`, { token: players[idx].token, body: { content: `我的词是${words[idx]}` } });
  })();
  ok('发言不能包含自己的词', !selfWordTry.ok);

  async function speakAllRound() {
    for (let step = 0; step < 4; step++) {
      const st = await api('GET', `/api/rooms/${roomId}`, { token: players[0].token });
      if (st.data.room.phase !== 'speak') return;
      const turn = st.data.room.turn_seat;
      const who = st.data.room.players.find((x) => x.seat === turn);
      const idx = players.findIndex((p) => p.user.id === who.user_id);
      await api('POST', `/api/rooms/${roomId}/speak`, { token: players[idx].token, body: { content: `这是一个很常见的东西，第${step}个描述` } });
    }
  }
  await speakAllRound();
  let st = await api('GET', `/api/rooms/${roomId}`, { token: players[0].token });
  ok('全员描述后进入投票', st.data.room.phase === 'vote', st.data.room.phase);

  // 平民全投卧底，卧底投别人 → 卧底出局 → 平民胜
  const seatOf = (idx) => st.data.room.players.find((x) => x.user_id === players[idx].user.id).seat;
  const spySeat = seatOf(spyIdx);
  for (let i = 0; i < 4; i++) {
    const target = i === spyIdx ? seatOf((spyIdx + 1) % 4) : spySeat;
    await api('POST', `/api/rooms/${roomId}/vote`, { token: players[i].token, body: { target_seat: target } });
  }
  const endEv = await streams[0].wait((e) => e.event === 'state' && e.data.status === 'ended', 8000, '游戏结束');
  ok('平民胜利结算', endEv.data.winner === 'civilian', endEv.data.winner);
  ok('结算复盘揭示身份与词', endEv.data.reveal?.length === 4 && endEv.data.reveal.some((r) => r.role === 'undercover'));
  const hostMsg = streams[0].events.filter((e) => e.event === 'msg' && e.data.kind === 'host');
  ok('AI 主持人全程主持（带AI标识）', hostMsg.length >= 4 && hostMsg.every((m) => m.data.is_ai));
  streams.forEach((s) => s.close());

  console.log('\n== 谁是卧底（1 真人 + AI 陪练补位） ==');
  const create2 = await api('POST', '/api/rooms', { token: u1.token, body: { name: 'AI陪练局', allow_bots: true } });
  const room2 = create2.data.room.id;
  const s2 = sse(`/api/rooms/${room2}/events`, u1.token);
  await api('POST', `/api/rooms/${room2}/ready`, { token: u1.token, body: { ready: true } });
  const start2 = await api('POST', `/api/rooms/${room2}/start`, { token: u1.token });
  ok('单人开局 AI 自动补位', start2.ok, JSON.stringify(start2));
  const word2 = await s2.wait((e) => e.event === 'word', 8000, 'AI局发词');
  ok('收到词语', !!word2.data.word);
  // 轮到自己时发言，其他时间等待；玩到游戏结束（AI 随机投票，最多 6 轮）
  let finished = false;
  for (let guard = 0; guard < 120 && !finished; guard++) {
    const cur = await api('GET', `/api/rooms/${room2}`, { token: u1.token });
    const r = cur.data.room;
    if (r.status === 'ended') { finished = true; break; }
    if (r.phase === 'speak' && r.players.find((x) => x.seat === r.turn_seat)?.user_id === u1.user.id) {
      await api('POST', `/api/rooms/${room2}/speak`, { token: u1.token, body: { content: '我觉得它在生活里很常见啦' } });
    } else if (r.phase === 'vote' && r.my_alive !== false && !r.players.find((x) => x.user_id === u1.user.id)?.voted) {
      const target = r.players.find((x) => x.alive && x.user_id !== u1.user.id);
      if (target) await api('POST', `/api/rooms/${room2}/vote`, { token: u1.token, body: { target_seat: target.seat } }).catch(() => {});
    }
    await new Promise((res) => setTimeout(res, 500));
  }
  ok('AI 陪练局完整跑完', finished);
  const aiPlayers = s2.events.find((e) => e.event === 'state')?.data.players.filter((p) => p.is_bot) || [];
  ok('AI 陪练带明确标识', aiPlayers.every((p) => p.ai_label === 'AI 陪练'));
  s2.close(); lobby.close();

  console.log('\n== 通知中心 ==');
  const inbox = await api('GET', '/api/notifications', { token: u1.token });
  ok('收到互动通知（赞/评论/关注）', inbox.ok && inbox.data.items.length >= 2 && inbox.data.unread > 0, `items=${inbox.data?.items?.length} unread=${inbox.data?.unread}`);
  const kinds = new Set(inbox.data.items.map((n) => n.kind));
  ok('通知类型覆盖', kinds.has('comment') || kinds.has('like') || kinds.has('follow'), [...kinds].join(','));
  await api('POST', '/api/notifications/read', { token: u1.token });
  const unread2 = await api('GET', '/api/me/unread', { token: u1.token });
  ok('一键已读', unread2.data.unread === 0);

  console.log('\n== 狼人杀（4 真人 + AI 补位完整对局） ==');
  const wfCreate = await api('POST', '/api/rooms', { token: u1.token, body: { name: '狼人杀测试局', game_type: 'werewolf', max_players: 8, allow_bots: true } });
  ok('创建狼人杀房间', wfCreate.ok, JSON.stringify(wfCreate));
  const wfId = wfCreate.data.room.id;
  const wfPlayers = [u1, ...guests];
  for (const g of guests) await api('POST', `/api/rooms/${wfId}/join`, { token: g.token });
  const wfStream = sse(`/api/rooms/${wfId}/events`, u1.token);
  for (const pl of wfPlayers) await api('POST', `/api/rooms/${wfId}/ready`, { token: pl.token, body: { ready: true } });
  const wfStart = await api('POST', `/api/rooms/${wfId}/start`, { token: u1.token });
  ok('开始游戏（AI 补位到 6 人）', wfStart.ok, JSON.stringify(wfStart));
  await new Promise((r) => setTimeout(r, 400));
  const roles = [];
  for (const pl of wfPlayers) {
    const st = await api('GET', `/api/rooms/${wfId}`, { token: pl.token });
    roles.push(st.data.room.my_role);
  }
  ok('私发身份（4 真人均有身份）', roles.every(Boolean) && roles.every((r) => ['wolf', 'seer', 'witch', 'villager'].includes(r)), roles.join(','));
  // 后台能看到进行中的房间
  const adminRooms = await api('GET', '/api/admin/rooms', { token: admin.token });
  ok('后台房间管理可见对局', adminRooms.ok && adminRooms.data.live.some((r) => r.id === wfId));

  let seerSawResult = false;
  let wfDone = false;
  for (let guard = 0; guard < 400 && !wfDone; guard++) {
    for (const pl of wfPlayers) {
      const cur = await api('GET', `/api/rooms/${wfId}`, { token: pl.token });
      const r = cur.data.room;
      if (r.status === 'ended') { wfDone = true; break; }
      const me = r.players.find((x) => x.user_id === pl.user.id);
      if (!me?.alive) continue;
      const n = r.my_night;
      try {
        if (r.phase === 'night' && n && !n.acted) {
          if (n.stage === 'wolf' && n.targets?.length) {
            await api('POST', `/api/rooms/${wfId}/action`, { token: pl.token, body: { action: 'kill', target_seat: n.targets[0].seat } });
          } else if (n.stage === 'seer' && n.targets?.length) {
            const res = await api('POST', `/api/rooms/${wfId}/action`, { token: pl.token, body: { action: 'check', target_seat: n.targets[0].seat } });
            if (res.ok && /身份是/.test(res.data.result || '')) seerSawResult = true;
          } else if (n.stage === 'witch') {
            const act = n.can_save ? 'save' : 'skip';
            await api('POST', `/api/rooms/${wfId}/action`, { token: pl.token, body: { action: act } });
          }
        } else if (r.phase === 'speak' && r.turn_seat === me.seat) {
          await api('POST', `/api/rooms/${wfId}/speak`, { token: pl.token, body: { content: '我是好人，先听大家的' } });
        } else if (r.phase === 'vote' && !me.voted) {
          const target = r.players.find((x) => x.alive && x.user_id !== pl.user.id);
          if (target) await api('POST', `/api/rooms/${wfId}/vote`, { token: pl.token, body: { target_seat: target.seat } });
        }
      } catch { /* 状态竞争属正常 */ }
    }
    if (!wfDone) await new Promise((r) => setTimeout(r, 300));
  }
  ok('狼人杀完整对局跑完', wfDone);
  const wfEnd = wfStream.events.filter((e) => e.event === 'state').pop();
  ok('胜负结算（好人/狼人）', ['good', 'wolf'].includes(wfEnd?.data?.winner), wfEnd?.data?.winner);
  ok('结算揭示全部身份', wfEnd?.data?.reveal?.length >= 6 && wfEnd.data.reveal.some((x) => x.role === 'wolf'));
  const seerHuman = roles.includes('seer');
  ok('预言家查验结果可见', !seerHuman || seerSawResult, `seerHuman=${seerHuman}`);
  const wfHost = wfStream.events.filter((e) => e.event === 'msg' && e.data.kind === 'host');
  ok('AI 主持人全程主持（天黑/天亮/投票）', wfHost.length >= 4);
  wfStream.close();

  console.log('\n== 灵阵 · AI 团队（多智能体协作） ==');
  const lzTok = guests[2].token;
  const lzMeta = await api('GET', '/api/agents/meta', { token: lzTok });
  ok('工具与策略元信息', lzMeta.ok && lzMeta.data.tools.some((t) => t.id === 'knowledge_search') && lzMeta.data.strategies.some((s) => s.id === 'orchestrate'));
  ok('每日运行额度可见', lzMeta.data.quota.limit > 0 && lzMeta.data.quota.used === 0);

  const lzTeams = await api('GET', '/api/teams', { token: lzTok });
  ok('内置团队模板 ≥4', lzTeams.data.templates.length >= 4, `got ${lzTeams.data.templates.length}`);
  const tpl = lzTeams.data.templates.find((t) => t.strategy === 'orchestrate');
  ok('编排模板含多名成员', tpl && tpl.members.length >= 3);

  const myAgent = await api('POST', '/api/agents', { token: lzTok, body: { name: '测试员·验', avatar: '🧪', role: '端到端验证', persona: '你负责验证产出是否达标', tools: ['text_stats', 'calculator', 'nonexistent_tool'] } });
  ok('新建智能体（非法工具被过滤）', myAgent.ok && myAgent.data.agent.tools.includes('calculator') && !myAgent.data.agent.tools.includes('nonexistent_tool'));

  const cloned = await api('POST', `/api/teams/${tpl.id}/clone`, { token: lzTok });
  ok('复制团队模板为我的', cloned.ok && cloned.data.team.mine === true && cloned.data.team.members.length === tpl.members.length);
  const teamId = cloned.data.team.id;

  const runRes = await api('POST', `/api/teams/${teamId}/run`, { token: lzTok, body: { task: '用一句话介绍「句灵」这款产品，并算一下 12 个月会员按 9.9 元/月一共多少钱' } });
  ok('发起团队运行', runRes.ok && runRes.data.run_id > 0, JSON.stringify(runRes));
  const runId = runRes.data.run_id;

  const runStream = sse(`/api/runs/${runId}/events`, lzTok);
  const doneEv = await runStream.wait((e) => e.event === 'done' || e.event === 'error', 20000, '团队运行完成');
  ok('运行完成（done 事件）', doneEv.event === 'done' && doneEv.data.status === 'done', JSON.stringify(doneEv.data?.status));
  const stepEvents = runStream.events.filter((e) => e.event === 'step');
  const phases = new Set(stepEvents.map((e) => e.data.phase));
  ok('编排官产出计划（plan）', phases.has('plan'));
  ok('成员实际产出（act ≥3）', stepEvents.filter((e) => e.data.phase === 'act' && e.data.status === 'done').length >= 3);
  ok('成员真实调用工具（tool）', phases.has('tool'));
  ok('总编整合（synthesize）', phases.has('synthesize'));
  runStream.close();

  const runFull = await api('GET', `/api/runs/${runId}`, { token: lzTok });
  ok('运行结果已持久化', runFull.data.run.status === 'done' && runFull.data.run.result.length > 50);
  ok('交付物为结构化报告', runFull.data.run.result.includes('团队交付') || runFull.data.run.result.includes('#'));
  ok('拆解计划已保存', Array.isArray(runFull.data.run.plan) && runFull.data.run.plan.length >= 1);
  ok('步骤逐条留痕（≥5）', runFull.data.steps.length >= 5);
  const lzMeta2 = await api('GET', '/api/agents/meta', { token: lzTok });
  ok('运行后额度递减', lzMeta2.data.quota.used === 1);

  const kbList = await api('GET', '/api/kb', { token: lzTok });
  ok('内置示例知识库存在', kbList.data.templates.length >= 1 && kbList.data.templates[0].chunk_count > 0);
  const search = await api('POST', `/api/kb/${kbList.data.templates[0].id}/search`, { token: lzTok, body: { query: '句灵 产品 定位' } });
  ok('知识库检索命中', search.ok && search.data.hits.length >= 1 && search.data.hits[0].text.includes('句灵'));
  const myKb = await api('POST', '/api/kb', { token: lzTok, body: { name: '我的测试库' } });
  const addDoc = await api('POST', `/api/kb/${myKb.data.kb.id}/docs`, { token: lzTok, body: { source: '便签', text: '露营装备清单：帐篷、防潮垫、天幕、营地灯、便携炉具。新手建议先租后买。' } });
  ok('文档入库并切片', addDoc.ok && addDoc.data.added >= 1);
  const mySearch = await api('POST', `/api/kb/${myKb.data.kb.id}/search`, { token: lzTok, body: { query: '露营 装备' } });
  ok('自建知识库可检索', mySearch.data.hits.length >= 1 && mySearch.data.hits[0].text.includes('帐篷'));

  const routeTeam = await api('POST', '/api/teams', { token: lzTok, body: { name: '路由小队', strategy: 'route', member_ids: [myAgent.data.agent.id, tpl.members[0].id] } });
  ok('新建路由团队', routeTeam.ok && routeTeam.data.team.strategy === 'route');
  const routeRun = await api('POST', `/api/teams/${routeTeam.data.team.id}/run`, { token: lzTok, body: { task: '计算 (199*12) 等于多少' } });
  const routeStream = sse(`/api/runs/${routeRun.data.run_id}/events`, lzTok);
  const routeDone = await routeStream.wait((e) => e.event === 'done' || e.event === 'error', 20000, '路由运行');
  ok('路由团队单点接管完成', routeDone.event === 'done' && routeDone.data.status === 'done');
  routeStream.close();

  // 圆桌论战：多轮互评
  const debateTeam = await api('POST', '/api/teams', { token: lzTok, body: { name: '论战小队', strategy: 'debate', max_rounds: 2, member_ids: [tpl.members[0].id, tpl.members[1].id] } });
  ok('新建论战团队', debateTeam.ok && debateTeam.data.team.strategy === 'debate');
  const debateRun = await api('POST', `/api/teams/${debateTeam.data.team.id}/run`, { token: lzTok, body: { task: '远程办公对早期创业团队利大于弊还是弊大于利' } });
  const debateStream = sse(`/api/runs/${debateRun.data.run_id}/events`, lzTok);
  const debateDone = await debateStream.wait((e) => e.event === 'done' || e.event === 'error', 20000, '论战运行');
  ok('论战团队运行完成', debateDone.event === 'done' && debateDone.data.status === 'done');
  debateStream.close();
  const debateFull = await api('GET', `/api/runs/${debateRun.data.run_id}`, { token: lzTok });
  ok('论战多轮（2 人 ×2 轮 ≥4 段产出）', debateFull.data.steps.filter((s) => s.phase === 'act' && s.status === 'done').length >= 4, `got ${debateFull.data.steps.filter((s) => s.phase === 'act').length}`);
  ok('论战含轮次分隔', debateFull.data.steps.some((s) => s.phase === 'system'));

  // 团队广场：发布 + 他人运行
  const pub = await api('POST', `/api/teams/${teamId}/publish`, { token: lzTok, body: { published: true } });
  ok('发布团队到广场', pub.ok && pub.data.published === true);
  const otherTok = guests[0].token;
  const gallery = await api('GET', '/api/teams/gallery', { token: otherTok });
  ok('广场可见已发布团队', gallery.data.items.some((t) => t.id === teamId));
  const otherView = await api('GET', `/api/teams/${teamId}`, { token: otherTok });
  ok('他人可查看已发布团队', otherView.ok && otherView.data.team.mine === false);
  const otherRun = await api('POST', `/api/teams/${teamId}/run`, { token: otherTok, body: { task: '推荐三个周末短途露营的好去处' } });
  ok('他人可运行已发布团队', otherRun.ok && otherRun.data.run_id > 0);
  const otherStream = sse(`/api/runs/${otherRun.data.run_id}/events`, otherTok);
  const otherDone = await otherStream.wait((e) => e.event === 'done' || e.event === 'error', 20000, '他人运行');
  ok('他人运行已发布团队完成', otherDone.event === 'done' && otherDone.data.status === 'done');
  otherStream.close();
  const unpub = await api('POST', `/api/teams/${teamId}/publish`, { token: lzTok, body: { published: false } });
  ok('取消发布', unpub.ok && unpub.data.published === false);

  // 后台监控与预算管控
  const ov = await api('GET', '/api/admin/agents/overview', { token: admin.token });
  ok('后台运行总览', ov.ok && ov.data.runs.total >= 3 && Array.isArray(ov.data.recent) && ov.data.recent.length >= 1);
  ok('后台统计用户资产', ov.data.totals.teams >= 1 && ov.data.totals.agents >= 1);
  const cfg = await api('PUT', '/api/admin/agents/config', { token: admin.token, body: { budget_micro: 8_000_000 } });
  ok('后台设置每日预算', cfg.ok && cfg.data.budget_micro === 8_000_000);
  ok('预算已生效', (await api('GET', '/api/admin/agents/overview', { token: admin.token })).data.budget_micro === 8_000_000);
  const adminRunView = await api('GET', `/api/admin/agents/runs/${runId}`, { token: admin.token });
  ok('后台可查看任意运行详情', adminRunView.ok && adminRunView.data.steps.length >= 5);
  const nonAdmin = await api('GET', '/api/admin/agents/overview', { token: lzTok });
  ok('非管理员无法访问监控', !nonAdmin.ok && nonAdmin.status === 403);

  // 定时触发器 + 站内动作工具
  ok('工具含站内动作 compose_card', lzMeta.data.tools.some((t) => t.id === 'compose_card'));
  ok('空任务的触发器被拒', !(await api('POST', '/api/triggers', { token: lzTok, body: { team_id: teamId, task: '' } })).ok);
  const trg = await api('POST', '/api/triggers', { token: lzTok, body: { team_id: teamId, name: '每日选题', task: '给句灵想 3 个今天适合发的文案选题', schedule_kind: 'interval', interval_min: 5 } });
  ok('创建定时任务（间隔钳到 ≥30）', trg.ok && trg.data.trigger.interval_min === 30 && trg.data.trigger.enabled === true);
  const trgDaily = await api('POST', '/api/triggers', { token: lzTok, body: { team_id: teamId, task: '每天早报', schedule_kind: 'daily', at_hour: 8, at_minute: 30 } });
  ok('创建每日定点任务', trgDaily.ok && trgDaily.data.trigger.schedule_kind === 'daily' && trgDaily.data.trigger.next_run_at > Date.now());
  const trgList = await api('GET', '/api/triggers', { token: lzTok });
  ok('定时任务列表与上限', trgList.data.items.length >= 2 && trgList.data.limits.max_triggers === 5);
  const trgRun = await api('POST', `/api/triggers/${trg.data.trigger.id}/run-now`, { token: lzTok });
  ok('立即运行定时任务', trgRun.ok && trgRun.data.run_id > 0);
  const trgStream = sse(`/api/runs/${trgRun.data.run_id}/events`, lzTok);
  await trgStream.wait((e) => e.event === 'done' || e.event === 'error', 20000, '触发运行');
  trgStream.close();
  const trgFull = await api('GET', `/api/runs/${trgRun.data.run_id}`, { token: lzTok });
  ok('触发运行标记来源 trigger', trgFull.data.run.source === 'trigger' && trgFull.data.run.status === 'done');
  ok('文案成员生成了预览卡（compose_card）', trgFull.data.steps.some((s) => s.tool === 'compose_card' && s.status === 'done'));
  const trgAfter = (await api('GET', '/api/triggers', { token: lzTok })).data.items.find((t) => t.id === trg.data.trigger.id);
  ok('立即运行不打乱原定计划', trgAfter.run_count === 1 && trgAfter.next_run_at === trg.data.trigger.next_run_at);
  ok('暂停定时任务', (await api('PATCH', `/api/triggers/${trg.data.trigger.id}`, { token: lzTok, body: { enabled: false } })).data.trigger.enabled === false);
  ok('删除定时任务', (await api('DELETE', `/api/triggers/${trgDaily.data.trigger.id}`, { token: lzTok })).ok);
  const trgSteal = await api('PATCH', `/api/triggers/${trg.data.trigger.id}`, { token: guests[0].token, body: { enabled: true } });
  ok('他人无法操作我的触发器', !trgSteal.ok && trgSteal.status === 404);

  const editTpl = await api('PATCH', `/api/teams/${tpl.id}`, { token: lzTok, body: { name: '改不动' } });
  ok('内置模板不可编辑', !editTpl.ok && editTpl.status === 403);

  console.log('\n== 后台系统开关 ==');
  const togOn = await api('PUT', '/api/admin/settings', { token: admin.token, body: { ai_moderation: true } });
  ok('开启 AI 机审开关', togOn.ok && togOn.data.ai_moderation === true);
  await api('PUT', '/api/admin/settings', { token: admin.token, body: { ai_moderation: false } });

  console.log('\n== 注销 ==');
  const deact = await api('POST', '/api/me/deactivate', { token: guests[1].token, body: { confirm: '确认注销' } });
  ok('注销账号', deact.ok);
  const ghost = await api('GET', '/api/me', { token: guests[1].token });
  ok('注销后令牌失效', ghost.status === 401);

  console.log(`\n========== 结果：${passed} 通过 / ${failed} 失败 ==========\n`);
} catch (e) {
  console.error('\n💥 冒烟测试异常：', e);
  failed++;
} finally {
  server.kill();
  try { fs.rmSync(DB, { force: true }); fs.rmSync(DB + '-wal', { force: true }); fs.rmSync(DB + '-shm', { force: true }); } catch { /* noop */ }
  process.exit(failed ? 1 : 0);
}
