import { GET, POST, openSSE, bad } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { jparse } from '../lib/util.js';
import { subscribe } from '../lib/hub.js';
import * as core from '../game/core.js';
import { undercoverEngine } from '../game/undercover.js';
import { werewolfEngine } from '../game/werewolf.js';
import { horrorEngine } from '../game/horror.js';

core.registerEngine(undercoverEngine);
core.registerEngine(werewolfEngine);
core.registerEngine(horrorEngine);

GET('/api/rooms', async (ctx) => {
  const mine = ctx.user ? core.findUserRoom(ctx.user.id) : null;
  return { items: core.listRooms(), my_room_id: mine?.id || null, games: core.engineList() };
});

POST('/api/rooms', async (ctx) => {
  const theme = jparse(ctx.user.equipped, {}).room_theme || null;   // 房间主题皮肤：纯外观
  const room = core.createRoom(ctx.user, {
    name: ctx.body.name,
    maxPlayers: ctx.body.max_players,
    allowBots: ctx.body.allow_bots !== false,
    gameType: String(ctx.body.game_type || 'undercover'),
    theme
  });
  return { room: core.privateStateFor(room, ctx.user.id) };
}, { auth: true });

GET('/api/rooms/:id', async (ctx) => {
  const room = core.getRoom(ctx.params.id);
  if (!room) {
    const ended = q.get('SELECT * FROM game_rooms WHERE id = ?', ctx.params.id);
    if (ended) return { room: { id: ended.id, name: ended.name, game_type: ended.game_type, status: 'ended', winner: ended.winner, players: [] }, messages: [] };
    throw bad('房间不存在');
  }
  const messages = q.all('SELECT * FROM room_messages WHERE room_id = ? ORDER BY id DESC LIMIT 60', room.id).reverse();
  return {
    room: core.privateStateFor(room, ctx.user?.id || 0),
    messages: messages.map((m) => ({ ...m, is_ai: m.user_id === 0 }))
  };
});

POST('/api/rooms/:id/join', async (ctx) => {
  const room = core.joinRoom(ctx.user, ctx.params.id);
  return { room: core.privateStateFor(room, ctx.user.id) };
}, { auth: true });

POST('/api/rooms/:id/leave', async (ctx) => { core.leaveRoom(ctx.user, ctx.params.id); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/ready', async (ctx) => { core.setReady(ctx.user, ctx.params.id, ctx.body.ready); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/start', async (ctx) => { core.startGame(ctx.user, ctx.params.id); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/chat', async (ctx) => { core.chat(ctx.user, ctx.params.id, ctx.body.content); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/speak', async (ctx) => { core.speak(ctx.user, ctx.params.id, ctx.body.content); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/vote', async (ctx) => { core.vote(ctx.user, ctx.params.id, ctx.body.target_seat); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/kick', async (ctx) => { core.kickPlayer(ctx.user, ctx.params.id, Number(ctx.body.seat)); return { done: true }; }, { auth: true });

// 游戏特殊行动（狼人杀夜间：kill / check / save / poison / skip）
POST('/api/rooms/:id/action', async (ctx) => {
  return core.action(ctx.user, ctx.params.id, ctx.body) || { done: true };
}, { auth: true });

// SSE：房间实时事件（state / msg / word / role / night / seer_result / wolf_chat / kicked / closed）
GET('/api/rooms/:id/events', async (ctx) => {
  const room = core.getRoom(ctx.params.id);
  if (!room) throw bad('房间不存在或已结束');
  const client = openSSE(ctx.req, ctx.res);
  subscribe(`room:${room.id}`, client, ctx.user?.id || 0);
  client.send('state', core.publicState(room));
  if (ctx.user) {
    // 重连恢复私有信息（词语/身份/夜间提示）
    const priv = core.privateStateFor(room, ctx.user.id);
    if (priv.my_word && room.status === 'playing') client.send('word', { word: priv.my_word, tip: '描述它，但别说出它！' });
    if (priv.my_role_info && room.status === 'playing') client.send('role', { role: priv.my_role, ...priv.my_role_info });
    if (priv.my_night) client.send('night', priv.my_night);
  }
}, { auth: true });

// SSE：大厅实时事件（rooms / notice——AI 暖场组局提醒）
GET('/api/lobby/events', async (ctx) => {
  const client = openSSE(ctx.req, ctx.res);
  subscribe('lobby', client, ctx.user?.id || 0);
  client.send('rooms', core.listRooms());
});
