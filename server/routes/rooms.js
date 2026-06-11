import { GET, POST, openSSE, bad } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { jparse } from '../lib/util.js';
import { subscribe } from '../lib/hub.js';
import * as game from '../game/undercover.js';

GET('/api/rooms', async (ctx) => {
  const mine = ctx.user ? game.findUserRoom(ctx.user.id) : null;
  return { items: game.listRooms(), my_room_id: mine?.id || null };
});

POST('/api/rooms', async (ctx) => {
  const theme = jparse(ctx.user.equipped, {}).room_theme || null;   // 房间主题皮肤：纯外观
  const room = game.createRoom(ctx.user, {
    name: ctx.body.name,
    maxPlayers: ctx.body.max_players,
    allowBots: ctx.body.allow_bots !== false,
    theme
  });
  return { room: game.privateStateFor(room, ctx.user.id) };
}, { auth: true });

GET('/api/rooms/:id', async (ctx) => {
  const room = game.getRoom(ctx.params.id);
  if (!room) {
    const ended = q.get('SELECT * FROM game_rooms WHERE id = ?', ctx.params.id);
    if (ended) return { room: { id: ended.id, name: ended.name, status: 'ended', winner: ended.winner, players: [] }, messages: [] };
    throw bad('房间不存在');
  }
  const messages = q.all('SELECT * FROM room_messages WHERE room_id = ? ORDER BY id DESC LIMIT 60', room.id).reverse();
  return {
    room: game.privateStateFor(room, ctx.user?.id || 0),
    messages: messages.map((m) => ({ ...m, is_ai: m.user_id === 0 }))
  };
});

POST('/api/rooms/:id/join', async (ctx) => {
  const room = game.joinRoom(ctx.user, ctx.params.id);
  return { room: game.privateStateFor(room, ctx.user.id) };
}, { auth: true });

POST('/api/rooms/:id/leave', async (ctx) => { game.leaveRoom(ctx.user, ctx.params.id); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/ready', async (ctx) => { game.setReady(ctx.user, ctx.params.id, ctx.body.ready); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/start', async (ctx) => { game.startGame(ctx.user, ctx.params.id); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/chat', async (ctx) => { game.chat(ctx.user, ctx.params.id, ctx.body.content); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/speak', async (ctx) => { game.speak(ctx.user, ctx.params.id, ctx.body.content); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/vote', async (ctx) => { game.vote(ctx.user, ctx.params.id, ctx.body.target_seat); return { done: true }; }, { auth: true });
POST('/api/rooms/:id/kick', async (ctx) => { game.kickPlayer(ctx.user, ctx.params.id, Number(ctx.body.seat)); return { done: true }; }, { auth: true });

// SSE：房间实时事件（state / msg / word / kicked / closed）
GET('/api/rooms/:id/events', async (ctx) => {
  const room = game.getRoom(ctx.params.id);
  if (!room) throw bad('房间不存在或已结束');
  const client = openSSE(ctx.req, ctx.res);
  subscribe(`room:${room.id}`, client, ctx.user?.id || 0);
  client.send('state', game.publicState(room));
  if (ctx.user) {
    const me = room.players.find((p) => p.userId === ctx.user.id);
    if (me?.word && room.status === 'playing') client.send('word', { word: me.word, tip: '描述它，但别说出它！' });
  }
}, { auth: true });

// SSE：大厅实时事件（rooms / notice——AI 暖场组局提醒）
GET('/api/lobby/events', async (ctx) => {
  const client = openSSE(ctx.req, ctx.res);
  subscribe('lobby', client, ctx.user?.id || 0);
  client.send('rooms', game.listRooms());
});
