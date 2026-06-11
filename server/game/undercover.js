// ============================================================
// 谁是卧底：轻量桌游引擎（内存权威状态 + SQLite 快照 + SSE 广播）
// 公平铁律：身份/词语随机分配，皮肤与付费不影响任何游戏逻辑。
// AI 主持人与 AI 陪练永远带明确标识，不伪装真人。
// ============================================================
import { q } from '../lib/db.js';
import { publish, publishTo } from '../lib/hub.js';
import { now, pick, randInt, shuffle, roomCode } from '../lib/util.js';
import { gateContent } from '../lib/moderation.js';
import { bad, denied, notFound } from '../lib/httpx.js';

const rooms = new Map(); // id -> runtime room

const BOT_NAMES = ['小句灵·糯米', '小句灵·团子', '小句灵·年糕', '小句灵·麻薯', '小句灵·汤圆', '小句灵·布丁'];
const BOT_AVATARS = ['blob_1', 'blob_2', 'blob_9', 'blob_10', 'blob_11', 'blob_3'];

const HOST_LINES = {
  welcome: ['欢迎来到「谁是卧底」！我是 AI 主持人句灵主持官～人齐后房主点开始就出发！', '叮咚～AI 主持人上线！准备好斗智斗勇了吗？'],
  start: ['词已经发到每个人手里啦，记住：描述要像，但别说破！', '游戏开始！看看谁是隐藏在我们之中的卧底——'],
  describeRound: ['第 {round} 轮描述开始，按座位顺序轮流发言～', '新一轮描述！注意听细节，卧底可能就在身边。'],
  yourTurn: ['轮到 {name} 描述啦，60 秒内说说你的词（不能直接说出来哦）', '{name}，到你了！给点线索又不暴露，看你的～'],
  voteStart: ['描述完毕！请大家投出你心中最可疑的人～', '投票时间到！相信你的直觉（或者推理）！'],
  voteTie: ['平票！本轮没有人出局，迷雾更浓了……', '票数打平，所有人暂时安全。下一轮见分晓！'],
  eliminated: ['{name} 被投出局，TA 的身份是——{role}！', '出局的是 {name}，身份揭晓：{role}！'],
  civWin: ['卧底被揪出来了！平民阵营胜利！🎉', '推理成功！卧底无处遁形，平民胜利！'],
  spyWin: ['卧底成功隐藏到了最后……卧底阵营胜利！🕶️', '居然没发现！卧底笑到了最后，卧底胜利！'],
  botSpeak: ['这个嘛……我觉得它挺常见的', '我的第一反应是开心的事', '它和日常生活离得很近', '嗯……说大不大，说小不小', '我会在特别的日子想起它', '它给人的感觉软软的', '不好形容，反正我挺喜欢', '年轻人应该都接触过', '看到它我会想到放假', '它有点上头，懂的都懂']
};
const fmt = (tpl, vars = {}) => tpl.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');

function hostSay(room, key, vars) {
  const content = fmt(pick(HOST_LINES[key]), vars);
  pushMsg(room, { userId: 0, nickname: 'AI 主持人 · 句灵主持官', kind: 'host', content });
}
function sysSay(room, content) {
  pushMsg(room, { userId: 0, nickname: '系统', kind: 'system', content });
}
function pushMsg(room, { userId, nickname, kind, content }) {
  const r = q.run(
    'INSERT INTO room_messages (room_id, user_id, nickname, kind, content, round, created_at) VALUES (?,?,?,?,?,?,?)',
    room.id, userId, nickname, kind, content, room.round, now()
  );
  publish(`room:${room.id}`, 'msg', {
    id: Number(r.lastInsertRowid), user_id: userId, nickname, kind, content,
    round: room.round, is_ai: userId === 0 || isBotUser(room, userId), created_at: now()
  });
}
const isBotUser = (room, userId) => room.players.some((p) => p.userId === userId && p.isBot);

// ---- 状态快照（公开信息永不包含他人词语/身份） ----
export function publicState(room) {
  return {
    id: room.id, name: room.name, game_type: 'undercover', status: room.status,
    host_id: room.hostId, max_players: room.maxPlayers, allow_bots: room.allowBots,
    theme: room.theme || null,
    round: room.round, phase: room.phase, turn_seat: room.turnSeat,
    phase_ends_at: room.phaseEndsAt || null,
    players: room.players.map((p) => ({
      seat: p.seat, user_id: p.userId, nickname: p.nickname, avatar: p.avatar,
      is_bot: p.isBot, ai_label: p.isBot ? 'AI 陪练' : null,
      ready: p.ready, alive: p.alive, voted: room.phase === 'vote' ? room.votes.has(p.seat) : undefined,
      spoke: room.phase === 'describe' ? room.spoken.has(p.seat) : undefined
    })),
    winner: room.winner || null,
    reveal: room.status === 'ended' ? room.reveal : null
  };
}
export function privateStateFor(room, userId) {
  const me = room.players.find((p) => p.userId === userId);
  return {
    ...publicState(room),
    my_seat: me?.seat ?? null,
    my_word: room.status === 'playing' && me?.alive !== undefined ? me?.word ?? null : null,
    my_alive: me?.alive ?? null
  };
}
function broadcast(room) {
  publish(`room:${room.id}`, 'state', publicState(room));
  persist(room);
}
function persist(room) {
  q.run(
    `UPDATE game_rooms SET status=?, round=?, winner=?, state=?, ended_at=? WHERE id=?`,
    room.status, room.round, room.winner || null,
    JSON.stringify({ phase: room.phase, players: room.players.length }),
    room.status === 'ended' ? now() : null, room.id
  );
}

// ---- 大厅 ----
export function listRooms() {
  const list = [];
  for (const room of rooms.values()) {
    if (room.status === 'ended') continue;
    list.push({
      id: room.id, name: room.name, game_type: 'undercover', status: room.status,
      players: room.players.length, max_players: room.maxPlayers,
      allow_bots: room.allowBots, theme: room.theme || null, created_at: room.createdAt
    });
  }
  return list.sort((a, b) => b.created_at - a.created_at);
}
export const lobbyChanged = () => publish('lobby', 'rooms', listRooms());
export const activeRoomCount = () => listRooms().length;

export function createRoom(user, { name, maxPlayers = 6, allowBots = true, theme = null }) {
  for (const r of rooms.values()) {
    if (r.status !== 'ended' && r.players.some((p) => p.userId === user.id)) {
      throw bad('你已经在一个房间里啦，先退出再开新房～', { room_id: r.id });
    }
  }
  const id = (() => { let c = roomCode(); while (rooms.has(c)) c = roomCode(); return c; })();
  const room = {
    id, name: String(name || `${user.nickname}的房间`).slice(0, 20), hostId: user.id,
    maxPlayers: Math.min(8, Math.max(4, maxPlayers | 0)), allowBots: !!allowBots, theme,
    status: 'waiting', phase: 'lobby', round: 0, turnSeat: null, phaseEndsAt: null,
    players: [], votes: new Map(), spoken: new Set(), winner: null, reveal: null,
    timers: [], createdAt: now()
  };
  rooms.set(id, room);
  q.run(
    'INSERT INTO game_rooms (id, name, game_type, status, host_id, max_players, allow_bots, theme, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
    id, room.name, 'undercover', 'waiting', user.id, room.maxPlayers, room.allowBots ? 1 : 0, theme, now()
  );
  seatPlayer(room, user, false);
  hostSay(room, 'welcome');
  lobbyChanged();
  return room;
}

function seatPlayer(room, user, isBot) {
  const seat = room.players.length;
  room.players.push({
    seat, userId: isBot ? -(seat + 1) : user.id,
    nickname: isBot ? user.nickname : user.nickname,
    avatar: user.avatar, isBot,
    ready: isBot, alive: true, word: null, role: null
  });
  return room.players[seat];
}

export function joinRoom(user, roomId) {
  const room = rooms.get(roomId);
  if (!room || room.status === 'ended') throw notFound('房间不存在或已结束');
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
  const [p] = room.players.splice(idx, 1);
  if (room.status === 'playing' && p.alive) {
    p.alive = false;
    sysSay(room, `${p.nickname} 离开了游戏（视为出局）`);
    room.players.splice(idx, 0, p); // 游戏中保留座位占位，仅标记出局
    const ended = checkWin(room);
    if (!ended) advanceAfterDeparture(room, p.seat);
  } else {
    room.players.forEach((x, i) => { x.seat = i; });
    sysSay(room, `${p.nickname} 离开了房间`);
  }
  if (!room.players.some((x) => !x.isBot)) return destroyRoom(room, '所有玩家已离开');
  if (room.hostId === user.id) {
    const human = room.players.find((x) => !x.isBot);
    if (human) { room.hostId = human.userId; sysSay(room, `${human.nickname} 成为新房主`); }
  }
  broadcast(room); lobbyChanged();
}

function destroyRoom(room, reason) {
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
  publishTo(`room:${room.id}`, p.userId, 'kicked', {});
  broadcast(room); lobbyChanged();
}

export function setReady(user, roomId, ready) {
  const room = mustRoom(roomId);
  const p = mustPlayer(room, user.id);
  if (room.status !== 'waiting') throw bad('游戏已开始');
  p.ready = !!ready;
  broadcast(room);
}

const mustRoom = (id) => { const r = rooms.get(id); if (!r || r.status === 'ended') throw notFound('房间不存在或已结束'); return r; };
const mustPlayer = (room, userId) => { const p = room.players.find((x) => x.userId === userId); if (!p) throw bad('你不在这个房间里'); return p; };

// ---- 开始游戏 ----
export function startGame(user, roomId) {
  const room = mustRoom(roomId);
  if (room.hostId !== user.id) throw denied('只有房主能开始游戏');
  if (room.status !== 'waiting') throw bad('游戏已经开始了');

  const humans = room.players.filter((p) => !p.isBot);
  if (!humans.every((p) => p.ready)) throw bad('还有小伙伴没准备好～');
  if (room.allowBots && room.players.length < 4) {
    const need = 4 - room.players.length;
    const used = new Set(room.players.map((p) => p.nickname));
    for (let i = 0; i < need; i++) {
      const ni = BOT_NAMES.findIndex((n) => !used.has(n));
      const nick = ni >= 0 ? BOT_NAMES[ni] : `小句灵·${i}号`;
      used.add(nick);
      seatPlayer(room, { nickname: nick, avatar: BOT_AVATARS[ni >= 0 ? ni : 0] }, true);
    }
    sysSay(room, `AI 陪练加入补位（共 ${need} 位，均带 AI 标识，仅供凑局练习）`);
  }
  if (room.players.length < 4) throw bad('至少需要 4 名玩家（可开启 AI 陪练补位）');

  const pairRow = q.get('SELECT * FROM word_pairs ORDER BY used_count ASC, RANDOM() LIMIT 1');
  if (!pairRow) throw bad('词库为空，请联系管理员');
  q.run('UPDATE word_pairs SET used_count = used_count + 1 WHERE id = ?', pairRow.id);
  const flip = Math.random() < 0.5;
  const civWord = flip ? pairRow.civilian : pairRow.undercover;
  const spyWord = flip ? pairRow.undercover : pairRow.civilian;

  const spyCount = room.players.length >= 7 ? 2 : 1;
  const seats = shuffle(room.players.map((p) => p.seat));
  const spySeats = new Set(seats.slice(0, spyCount));
  for (const p of room.players) {
    p.alive = true;
    p.role = spySeats.has(p.seat) ? 'undercover' : 'civilian';
    p.word = spySeats.has(p.seat) ? spyWord : civWord;
  }
  room.status = 'playing';
  room.round = 1;
  room.winner = null;
  room.reveal = null;
  q.run("UPDATE game_rooms SET status='playing' WHERE id=?", room.id);

  hostSay(room, 'start');
  for (const p of room.players) {
    if (!p.isBot) publishTo(`room:${room.id}`, p.userId, 'word', { word: p.word, tip: '描述它，但别说出它！' });
  }
  beginDescribe(room);
  lobbyChanged();
}

// ---- 描述阶段（按座位轮流，非线性时长：真人 60s，AI 1.5~3.5s） ----
function beginDescribe(room) {
  room.phase = 'describe';
  room.spoken = new Set();
  room.votes = new Map();
  hostSay(room, 'describeRound', { round: room.round });
  nextTurn(room);
}
function aliveSeats(room) { return room.players.filter((p) => p.alive).map((p) => p.seat).sort((a, b) => a - b); }

function nextTurn(room) {
  clearTimers(room);
  const seats = aliveSeats(room).filter((s) => !room.spoken.has(s));
  if (!seats.length) return beginVote(room);
  room.turnSeat = seats[0];
  const p = room.players.find((x) => x.seat === room.turnSeat);
  if (p.isBot) {
    room.phaseEndsAt = now() + 3500;
    broadcast(room);
    addTimer(room, randInt(1500, 3500), () => {
      botDescribe(room, p);
    });
  } else {
    room.phaseEndsAt = now() + 60_000;
    hostSay(room, 'yourTurn', { name: p.nickname });
    broadcast(room);
    addTimer(room, 60_000, () => {
      sysSay(room, `${p.nickname} 超时未发言，自动跳过`);
      room.spoken.add(p.seat);
      nextTurn(room);
    });
  }
}
function botDescribe(room, p) {
  if (room.phase !== 'describe' || room.turnSeat !== p.seat) return;
  pushMsg(room, { userId: p.userId, nickname: p.nickname, kind: 'speak', content: pick(HOST_LINES.botSpeak) });
  room.spoken.add(p.seat);
  nextTurn(room);
}

export function speak(user, roomId, content) {
  const room = mustRoom(roomId);
  const p = mustPlayer(room, user.id);
  if (room.phase !== 'describe') throw bad('现在不是描述阶段');
  if (room.turnSeat !== p.seat) throw bad('还没轮到你哦，听听别人怎么说～');
  const text = String(content || '').trim().slice(0, 100);
  if (!text) throw bad('说点什么吧');
  if (p.word && text.includes(p.word)) throw bad('描述里不能直接说出你的词哦！');
  const gate = gateContent(text);
  if (!gate.allowed || gate.status === 'pending') throw bad(gate.notice || '这句话不太合适，换个说法吧');
  pushMsg(room, { userId: p.userId, nickname: p.nickname, kind: 'speak', content: text });
  room.spoken.add(p.seat);
  nextTurn(room);
}

// ---- 投票阶段 ----
function beginVote(room) {
  clearTimers(room);
  room.phase = 'vote';
  room.turnSeat = null;
  room.votes = new Map();
  room.phaseEndsAt = now() + 45_000;
  hostSay(room, 'voteStart');
  broadcast(room);
  for (const p of room.players.filter((x) => x.alive && x.isBot)) {
    addTimer(room, randInt(2000, 8000), () => {
      if (room.phase !== 'vote' || room.votes.has(p.seat)) return;
      const targets = aliveSeats(room).filter((s) => s !== p.seat);
      castVote(room, p, pick(targets));
    });
  }
  addTimer(room, 45_000, () => tallyVotes(room, true));
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
  castVote(room, p, target.seat);
}

function castVote(room, p, targetSeat) {
  room.votes.set(p.seat, targetSeat);
  sysSay(room, `${p.nickname} 已投票（${room.votes.size}/${aliveSeats(room).length}）`);
  broadcast(room);
  if (room.votes.size >= aliveSeats(room).length) tallyVotes(room, false);
}

function tallyVotes(room, timedOut) {
  if (room.phase !== 'vote') return;
  clearTimers(room);
  if (timedOut) sysSay(room, '投票时间结束');
  const counts = new Map();
  for (const t of room.votes.values()) counts.set(t, (counts.get(t) || 0) + 1);
  let max = 0; let top = [];
  for (const [seat, c] of counts) {
    if (c > max) { max = c; top = [seat]; }
    else if (c === max) top.push(seat);
  }
  const detail = [...counts.entries()].map(([s, c]) => `${room.players.find((p) => p.seat === s)?.nickname} ${c}票`).join('，') || '无人投票';
  sysSay(room, `开票：${detail}`);

  if (top.length !== 1 || max === 0) {
    hostSay(room, 'voteTie');
    return nextRoundOrEnd(room);
  }
  const out = room.players.find((p) => p.seat === top[0]);
  out.alive = false;
  hostSay(room, 'eliminated', { name: out.nickname, role: out.role === 'undercover' ? '卧底！' : '平民' });
  if (!checkWin(room)) nextRoundOrEnd(room);
}

function nextRoundOrEnd(room) {
  if (room.round >= 6) {
    return endGame(room, 'undercover', '回合数耗尽，卧底成功潜伏到最后');
  }
  room.round += 1;
  addTimer(room, 2500, () => beginDescribe(room));
  broadcast(room);
}

function advanceAfterDeparture(room, seat) {
  if (room.phase === 'describe' && room.turnSeat === seat) nextTurn(room);
  if (room.phase === 'vote' && room.votes.size >= aliveSeats(room).length) tallyVotes(room, false);
}

function checkWin(room) {
  const alive = room.players.filter((p) => p.alive);
  const spies = alive.filter((p) => p.role === 'undercover').length;
  const civs = alive.length - spies;
  if (spies === 0) { endGame(room, 'civilian'); return true; }
  if (spies >= civs) { endGame(room, 'undercover'); return true; }
  return false;
}

function endGame(room, winner, extra = '') {
  clearTimers(room);
  room.status = 'ended';
  room.phase = 'ended';
  room.winner = winner;
  room.turnSeat = null;
  room.reveal = room.players.map((p) => ({ seat: p.seat, nickname: p.nickname, role: p.role, word: p.word, is_bot: p.isBot }));
  if (extra) sysSay(room, extra);
  hostSay(room, winner === 'civilian' ? 'civWin' : 'spyWin');
  sysSay(room, '词语揭晓：' + room.reveal.map((r) => `${r.nickname}「${r.word}」(${r.role === 'undercover' ? '卧底' : '平民'})`).join('；'));
  broadcast(room);
  persist(room);
  rooms.delete(room.id);   // 复盘信息已随 ended 状态广播；房间从大厅移除
  lobbyChanged();
}

// ---- 聊天（任意阶段可用；与发言区分开） ----
export function chat(user, roomId, content) {
  const room = mustRoom(roomId);
  const p = mustPlayer(room, user.id);
  const text = String(content || '').trim().slice(0, 200);
  if (!text) throw bad('说点什么吧');
  const gate = gateContent(text);
  if (!gate.allowed) throw bad(gate.notice);
  if (gate.care) throw bad(gate.notice);   // 自伤风险：私下温柔提醒，不在游戏房间扩散
  pushMsg(room, { userId: p.userId, nickname: p.nickname, kind: 'chat', content: text });
}

// ---- 定时器管理 ----
function addTimer(room, ms, fn) {
  const t = setTimeout(() => {
    room.timers = room.timers.filter((x) => x !== t);
    try { fn(); } catch (e) { console.error('[game timer]', e); }
  }, ms);
  room.timers.push(t);
}
function clearTimers(room) {
  for (const t of room.timers) clearTimeout(t);
  room.timers = [];
  room.phaseEndsAt = null;
}

export function getRoom(id) { return rooms.get(id) || null; }
export function findUserRoom(userId) {
  for (const r of rooms.values()) {
    if (r.status !== 'ended' && r.players.some((p) => p.userId === userId)) return r;
  }
  return null;
}

// 服务器重启后，把数据库里残留的进行中房间标记为结束
export function recoverOnBoot() {
  q.run("UPDATE game_rooms SET status='ended', ended_at=? WHERE status != 'ended'", now());
}
