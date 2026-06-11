// ============================================================
// 桌游框架核心：房间管理 / 座位 / 消息 / 广播 / 计时器 / 大厅
// 游戏模块实现 engine 接口：
//   { type, name, icon, minPlayers, maxPlayers,
//     onStart(room), onSpeak(room,p,text), onVote(room,p,seat),
//     onAction(room,p,body), onLeave(room,p), decorateState(room,state,userId) }
// 公平铁律：皮肤与付费状态对引擎不可见；AI 主持/陪练永远带标识。
// ============================================================
import { q } from '../lib/db.js';
import { publish, publishTo } from '../lib/hub.js';
import { now, pick, shuffle, roomCode } from '../lib/util.js';
import { gateContent } from '../lib/moderation.js';
import { bad, denied, notFound } from '../lib/httpx.js';

const rooms = new Map();
const engines = new Map();
export const registerEngine = (e) => engines.set(e.type, e);
export const engineList = () => [...engines.values()].map((e) => ({ type: e.type, name: e.name, icon: e.icon, min: e.minPlayers, max: e.maxPlayers }));

export const BOT_NAMES = ['小句灵·糯米', '小句灵·团子', '小句灵·年糕', '小句灵·麻薯', '小句灵·汤圆', '小句灵·布丁', '小句灵·芋圆', '小句灵·椰果', '小句灵·奶盖', '小句灵·西米', '小句灵·青稞'];
const BOT_AVATARS = ['blob_1', 'blob_2', 'blob_9', 'blob_10', 'blob_11', 'blob_3', 'blob_4', 'blob_5', 'blob_6', 'blob_7', 'blob_8'];

// ---- 消息 ----
export function pushMsg(room, { userId, nickname, kind, content }) {
  const r = q.run(
    'INSERT INTO room_messages (room_id, user_id, nickname, kind, content, round, created_at) VALUES (?,?,?,?,?,?,?)',
    room.id, userId, nickname, kind, content, room.round, now()
  );
  publish(`room:${room.id}`, 'msg', {
    id: Number(r.lastInsertRowid), user_id: userId, nickname, kind, content,
    round: room.round, is_ai: userId === 0 || isBot(room, userId), created_at: now()
  });
}
export const hostSay = (room, content) => pushMsg(room, { userId: 0, nickname: 'AI 主持人 · 句灵主持官', kind: 'host', content });
export const sysSay = (room, content) => pushMsg(room, { userId: 0, nickname: '系统', kind: 'system', content });
export const tell = (room, userId, event, data) => publishTo(`room:${room.id}`, userId, event, data);
const isBot = (room, userId) => room.players.some((p) => p.userId === userId && p.isBot);

// ---- 状态 ----
export function publicState(room) {
  return {
    id: room.id, name: room.name, game_type: room.engine.type, game_name: room.engine.name,
    status: room.status, host_id: room.hostId, max_players: room.maxPlayers,
    allow_bots: room.allowBots, theme: room.theme || null,
    round: room.round, phase: room.phase, stage: room.stage || null, turn_seat: room.turnSeat,
    phase_ends_at: room.phaseEndsAt || null,
    players: room.players.map((p) => ({
      seat: p.seat, user_id: p.userId, nickname: p.nickname, avatar: p.avatar,
      is_bot: p.isBot, ai_label: p.isBot ? 'AI 陪练' : null,
      ready: p.ready, alive: p.alive,
      voted: room.phase === 'vote' ? room.votes.has(p.seat) : undefined,
      spoke: room.phase === 'speak' ? room.spoken.has(p.seat) : undefined
    })),
    winner: room.winner || null,
    reveal: room.status === 'ended' ? room.reveal : null
  };
}
export function privateStateFor(room, userId) {
  const me = room.players.find((p) => p.userId === userId);
  const base = {
    ...publicState(room),
    my_seat: me?.seat ?? null,
    my_alive: me?.alive ?? null
  };
  return room.engine.decorateState ? room.engine.decorateState(room, base, userId, me) : base;
}
export function broadcast(room) {
  publish(`room:${room.id}`, 'state', publicState(room));
  persist(room);
}
export function persist(room) {
  q.run(
    'UPDATE game_rooms SET status=?, round=?, winner=?, state=?, ended_at=? WHERE id=?',
    room.status, room.round, room.winner || null,
    JSON.stringify({ phase: room.phase, stage: room.stage, players: room.players.length }),
    room.status === 'ended' ? now() : null, room.id
  );
}

// ---- 大厅 ----
export function listRooms() {
  const list = [];
  for (const room of rooms.values()) {
    if (room.status === 'ended') continue;
    list.push({
      id: room.id, name: room.name, game_type: room.engine.type, game_name: room.engine.name, icon: room.engine.icon,
      status: room.status, players: room.players.length, max_players: room.maxPlayers,
      allow_bots: room.allowBots, theme: room.theme || null, created_at: room.createdAt
    });
  }
  return list.sort((a, b) => b.created_at - a.created_at);
}
export const lobbyChanged = () => publish('lobby', 'rooms', listRooms());
export const activeRoomCount = () => listRooms().length;
export const getRoom = (id) => rooms.get(id) || null;
export function findUserRoom(userId) {
  for (const r of rooms.values()) {
    if (r.status !== 'ended' && r.players.some((p) => p.userId === userId)) return r;
  }
  return null;
}
export const allRooms = () => [...rooms.values()];

// ---- 房间生命周期 ----
export function createRoom(user, { name, maxPlayers, allowBots = true, theme = null, gameType = 'undercover' }) {
  const engine = engines.get(gameType);
  if (!engine) throw bad('暂不支持这个玩法');
  const existing = findUserRoom(user.id);
  if (existing) throw bad('你已经在一个房间里啦，先退出再开新房～', { room_id: existing.id });
  let id = roomCode();
  while (rooms.has(id)) id = roomCode();
  const room = {
    id, engine, name: String(name || `${user.nickname}的${engine.name}`).slice(0, 20),
    hostId: user.id,
    maxPlayers: Math.min(engine.maxPlayers, Math.max(engine.minPlayers, (maxPlayers | 0) || engine.defaultPlayers || engine.minPlayers)),
    allowBots: !!allowBots, theme,
    status: 'waiting', phase: 'lobby', stage: null, round: 0, turnSeat: null, phaseEndsAt: null,
    players: [], votes: new Map(), spoken: new Set(), winner: null, reveal: null,
    timers: [], createdAt: now(), g: {}      // g = 引擎私有状态
  };
  rooms.set(id, room);
  q.run(
    'INSERT INTO game_rooms (id, name, game_type, status, host_id, max_players, allow_bots, theme, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
    id, room.name, engine.type, 'waiting', user.id, room.maxPlayers, room.allowBots ? 1 : 0, theme, now()
  );
  seatPlayer(room, user, false);
  hostSay(room, engine.welcome ? pick(engine.welcome) : `欢迎来到「${engine.name}」！我是 AI 主持人，人齐后房主点开始～`);
  lobbyChanged();
  return room;
}

function seatPlayer(room, user, bot) {
  const p = {
    seat: room.players.length,
    userId: bot ? -(room.players.length + 1 + Math.floor(Math.random() * 1000)) : user.id,
    nickname: user.nickname, avatar: user.avatar,
    isBot: bot, ready: bot, alive: true, role: null, word: null
  };
  room.players.push(p);
  return p;
}

export function joinRoom(user, roomId) {
  const room = mustRoom(roomId);
  if (room.players.some((p) => p.userId === user.id)) return room;
  if (room.status !== 'waiting') throw bad('游戏已经开始，下一局再来吧～');
  if (room.players.length >= room.maxPlayers) throw bad('房间满啦');
  seatPlayer(room, user, false);
  sysSay(room, `${user.nickname} 进入了房间`);
  broadcast(room); lobbyChanged();
  return room;
}

export function leaveRoom(user, roomId) {
  const room = rooms.get(roomId);
  if (!room) return;
  const idx = room.players.findIndex((p) => p.userId === user.id);
  if (idx < 0) return;
  const p = room.players[idx];
  if (room.status === 'playing' && p.alive) {
    p.alive = false;
    p.left = true;
    sysSay(room, `${p.nickname} 离开了游戏（视为出局）`);
    room.engine.onLeave?.(room, p);
  } else if (room.status !== 'playing') {
    room.players.splice(idx, 1);
    room.players.forEach((x, i) => { x.seat = i; });
    sysSay(room, `${p.nickname} 离开了房间`);
  }
  if (!room.players.some((x) => !x.isBot && !x.left)) return destroyRoom(room, '所有玩家已离开');
  if (room.hostId === user.id) {
    const human = room.players.find((x) => !x.isBot && !x.left);
    if (human) { room.hostId = human.userId; sysSay(room, `${human.nickname} 成为新房主`); }
  }
  if (room.status !== 'ended') { broadcast(room); lobbyChanged(); }
}

export function destroyRoom(room, reason) {
  clearTimers(room);
  room.status = 'ended';
  room.phase = 'ended';
  persist(room);
  publish(`room:${room.id}`, 'closed', { reason });
  rooms.delete(room.id);
  lobbyChanged();
}

export function kickPlayer(user, roomId, seat) {
  const room = mustRoom(roomId);
  if (room.hostId !== user.id) throw denied('只有房主可以请人离开');
  if (room.status !== 'waiting') throw bad('游戏开始后不能踢人');
  const p = room.players.find((x) => x.seat === seat);
  if (!p || p.userId === user.id) throw bad('无效的座位');
  room.players = room.players.filter((x) => x !== p);
  room.players.forEach((x, i) => { x.seat = i; });
  sysSay(room, `${p.nickname} 被房主请离了房间`);
  tell(room, p.userId, 'kicked', {});
  broadcast(room); lobbyChanged();
}

export function setReady(user, roomId, ready) {
  const room = mustRoom(roomId);
  const p = mustPlayer(room, user.id);
  if (room.status !== 'waiting') throw bad('游戏已开始');
  p.ready = !!ready;
  broadcast(room);
}

export function startGame(user, roomId) {
  const room = mustRoom(roomId);
  if (room.hostId !== user.id) throw denied('只有房主能开始游戏');
  if (room.status !== 'waiting') throw bad('游戏已经开始了');
  const humans = room.players.filter((p) => !p.isBot);
  if (!humans.every((p) => p.ready)) throw bad('还有小伙伴没准备好～');
  const min = room.engine.minPlayers;
  if (room.allowBots && room.players.length < min) {
    const need = Math.min(min - room.players.length, room.maxPlayers - room.players.length);
    const used = new Set(room.players.map((p) => p.nickname));
    for (let i = 0; i < need; i++) {
      const ni = BOT_NAMES.findIndex((n) => !used.has(n));
      const nick = ni >= 0 ? BOT_NAMES[ni] : `小句灵·${i}号`;
      used.add(nick);
      seatPlayer(room, { nickname: nick, avatar: BOT_AVATARS[ni >= 0 ? ni : 0] }, true);
    }
    sysSay(room, `AI 陪练加入补位（共 ${need} 位，均带 AI 标识，仅供凑局练习）`);
  }
  if (room.players.length < min) throw bad(`「${room.engine.name}」至少需要 ${min} 名玩家（可开启 AI 陪练补位）`);
  room.status = 'playing';
  room.round = 1;
  room.winner = null;
  room.reveal = null;
  q.run("UPDATE game_rooms SET status='playing' WHERE id=?", room.id);
  room.engine.onStart(room);
  lobbyChanged();
}

export function endGame(room, winner, revealRows, finale) {
  clearTimers(room);
  room.status = 'ended';
  room.phase = 'ended';
  room.stage = null;
  room.winner = winner;
  room.turnSeat = null;
  room.reveal = revealRows;
  if (finale) hostSay(room, finale);
  broadcast(room);
  persist(room);
  rooms.delete(room.id);
  lobbyChanged();
}

// ---- 玩家动作分发 ----
export const mustRoom = (id) => { const r = rooms.get(id); if (!r || r.status === 'ended') throw notFound('房间不存在或已结束'); return r; };
export const mustPlayer = (room, userId) => { const p = room.players.find((x) => x.userId === userId); if (!p) throw bad('你不在这个房间里'); return p; };

export function speak(user, roomId, content) {
  const room = mustRoom(roomId);
  const p = mustPlayer(room, user.id);
  const text = String(content || '').trim().slice(0, 120);
  if (!text) throw bad('说点什么吧');
  const gate = gateContent(text);
  if (!gate.allowed || gate.status === 'pending') throw bad(gate.notice || '这句话不太合适，换个说法吧');
  room.engine.onSpeak(room, p, text);
}

export function vote(user, roomId, targetSeat) {
  const room = mustRoom(roomId);
  const p = mustPlayer(room, user.id);
  if (room.phase !== 'vote') throw bad('现在不是投票阶段');
  if (!p.alive) throw bad('出局后不能投票，安静吃瓜～');
  if (room.votes.has(p.seat)) throw bad('你已经投过票啦');
  const target = room.players.find((x) => x.seat === Number(targetSeat));
  if (!target || !target.alive) throw bad('投票目标无效');
  if (target.seat === p.seat) throw bad('不能投自己哦');
  room.engine.onVote(room, p, target.seat);
}

export function action(user, roomId, body) {
  const room = mustRoom(roomId);
  const p = mustPlayer(room, user.id);
  if (room.status !== 'playing') throw bad('游戏还没开始');
  if (!room.engine.onAction) throw bad('这个玩法没有特殊操作');
  return room.engine.onAction(room, p, body || {});
}

export function chat(user, roomId, content) {
  const room = mustRoom(roomId);
  const p = mustPlayer(room, user.id);
  const text = String(content || '').trim().slice(0, 200);
  if (!text) throw bad('说点什么吧');
  const gate = gateContent(text);
  if (!gate.allowed || gate.care) throw bad(gate.notice);
  // 夜晚禁止公屏聊天（狼人杀防场外信息）
  if (room.phase === 'night' && p.alive) throw bad('天黑请闭眼，现在不能说话哦 🤫');
  pushMsg(room, { userId: p.userId, nickname: p.nickname, kind: 'chat', content: text });
}

// ---- 通用投票计票（平票=无人出局，返回出局者或 null） ----
export function tallyVotes(room) {
  const counts = new Map();
  for (const t of room.votes.values()) counts.set(t, (counts.get(t) || 0) + 1);
  let max = 0; let top = [];
  for (const [seat, c] of counts) {
    if (c > max) { max = c; top = [seat]; }
    else if (c === max) top.push(seat);
  }
  const detail = [...counts.entries()]
    .map(([s, c]) => `${room.players.find((p) => p.seat === s)?.nickname} ${c}票`).join('，') || '无人投票';
  sysSay(room, `开票：${detail}`);
  if (top.length !== 1 || max === 0) return null;
  return room.players.find((p) => p.seat === top[0]);
}

// ---- 计时器 ----
export function addTimer(room, ms, fn) {
  const t = setTimeout(() => {
    room.timers = room.timers.filter((x) => x !== t);
    try { fn(); } catch (e) { console.error('[game timer]', e); }
  }, ms);
  room.timers.push(t);
  return t;
}
export function clearTimers(room) {
  for (const t of room.timers) clearTimeout(t);
  room.timers = [];
  room.phaseEndsAt = null;
}
export const aliveSeats = (room) => room.players.filter((p) => p.alive).map((p) => p.seat).sort((a, b) => a - b);
export const alivePlayers = (room) => room.players.filter((p) => p.alive);
export { shuffle, pick };

export function recoverOnBoot() {
  q.run("UPDATE game_rooms SET status='ended', ended_at=? WHERE status != 'ended'", now());
}
