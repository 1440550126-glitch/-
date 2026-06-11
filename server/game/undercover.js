// 谁是卧底：游戏引擎模块（房间底座见 core.js）
import { q } from '../lib/db.js';
import { now, pick, randInt, shuffle } from '../lib/util.js';
import { bad } from '../lib/httpx.js';
import * as core from './core.js';

const LINES = {
  welcome: ['欢迎来到「谁是卧底」！我是 AI 主持人句灵主持官～人齐后房主点开始就出发！', '叮咚～AI 主持人上线！准备好斗智斗勇了吗？'],
  start: ['词已经发到每个人手里啦，记住：描述要像，但别说破！', '游戏开始！看看谁是隐藏在我们之中的卧底——'],
  round: ['第 {round} 轮描述开始，按座位顺序轮流发言～', '新一轮描述！注意听细节，卧底可能就在身边。'],
  turn: ['轮到 {name} 描述啦，60 秒内说说你的词（不能直接说出来哦）', '{name}，到你了！给点线索又不暴露，看你的～'],
  voteStart: ['描述完毕！请大家投出你心中最可疑的人～', '投票时间到！相信你的直觉（或者推理）！'],
  tie: ['平票！本轮没有人出局，迷雾更浓了……', '票数打平，所有人暂时安全。下一轮见分晓！'],
  out: ['{name} 被投出局，TA 的身份是——{role}！', '出局的是 {name}，身份揭晓：{role}！'],
  civWin: ['卧底被揪出来了！平民阵营胜利！🎉', '推理成功！卧底无处遁形，平民胜利！'],
  spyWin: ['卧底成功隐藏到了最后……卧底阵营胜利！🕶️', '居然没发现！卧底笑到了最后，卧底胜利！'],
  botSpeak: ['这个嘛……我觉得它挺常见的', '我的第一反应是开心的事', '它和日常生活离得很近', '嗯……说大不大，说小不小', '我会在特别的日子想起它', '它给人的感觉软软的', '不好形容，反正我挺喜欢', '年轻人应该都接触过', '看到它我会想到放假', '它有点上头，懂的都懂']
};
const fmt = (tpl, vars = {}) => tpl.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
const say = (room, key, vars) => core.hostSay(room, fmt(pick(LINES[key]), vars));

function beginDescribe(room) {
  room.phase = 'speak';
  room.spoken = new Set();
  room.votes = new Map();
  say(room, 'round', { round: room.round });
  nextTurn(room);
}

function nextTurn(room) {
  core.clearTimers(room);
  const seats = core.aliveSeats(room).filter((s) => !room.spoken.has(s));
  if (!seats.length) return beginVote(room);
  room.turnSeat = seats[0];
  const p = room.players.find((x) => x.seat === room.turnSeat);
  if (p.isBot) {
    room.phaseEndsAt = now() + 3500;
    core.broadcast(room);
    core.addTimer(room, randInt(1500, 3500), () => {
      if (room.phase !== 'speak' || room.turnSeat !== p.seat) return;
      core.pushMsg(room, { userId: p.userId, nickname: p.nickname, kind: 'speak', content: pick(LINES.botSpeak) });
      room.spoken.add(p.seat);
      nextTurn(room);
    });
  } else {
    room.phaseEndsAt = now() + 60_000;
    say(room, 'turn', { name: p.nickname });
    core.broadcast(room);
    core.addTimer(room, 60_000, () => {
      core.sysSay(room, `${p.nickname} 超时未发言，自动跳过`);
      room.spoken.add(p.seat);
      nextTurn(room);
    });
  }
}

function beginVote(room) {
  core.clearTimers(room);
  room.phase = 'vote';
  room.turnSeat = null;
  room.votes = new Map();
  room.phaseEndsAt = now() + 45_000;
  say(room, 'voteStart');
  core.broadcast(room);
  for (const p of core.alivePlayers(room).filter((x) => x.isBot)) {
    core.addTimer(room, randInt(2000, 8000), () => {
      if (room.phase !== 'vote' || room.votes.has(p.seat)) return;
      const targets = core.aliveSeats(room).filter((s) => s !== p.seat);
      cast(room, p, pick(targets));
    });
  }
  core.addTimer(room, 45_000, () => settle(room, true));
}

function cast(room, p, targetSeat) {
  room.votes.set(p.seat, targetSeat);
  core.sysSay(room, `${p.nickname} 已投票（${room.votes.size}/${core.aliveSeats(room).length}）`);
  core.broadcast(room);
  if (room.votes.size >= core.aliveSeats(room).length) settle(room, false);
}

function settle(room, timedOut) {
  if (room.phase !== 'vote') return;
  core.clearTimers(room);
  if (timedOut) core.sysSay(room, '投票时间结束');
  const out = core.tallyVotes(room);
  if (!out) {
    say(room, 'tie');
    return nextRoundOrEnd(room);
  }
  out.alive = false;
  say(room, 'out', { name: out.nickname, role: out.role === 'undercover' ? '卧底！' : '平民' });
  if (!checkWin(room)) nextRoundOrEnd(room);
}

function nextRoundOrEnd(room) {
  if (room.round >= 6) return finish(room, 'undercover', '回合数耗尽，卧底成功潜伏到最后');
  room.round += 1;
  core.addTimer(room, 2500, () => beginDescribe(room));
  core.broadcast(room);
}

function checkWin(room) {
  const alive = core.alivePlayers(room);
  const spies = alive.filter((p) => p.role === 'undercover').length;
  if (spies === 0) { finish(room, 'civilian'); return true; }
  if (spies >= alive.length - spies) { finish(room, 'undercover'); return true; }
  return false;
}

function finish(room, winner, extra = '') {
  if (extra) core.sysSay(room, extra);
  say(room, winner === 'civilian' ? 'civWin' : 'spyWin');
  const reveal = room.players.map((p) => ({ seat: p.seat, nickname: p.nickname, role: p.role, word: p.word, is_bot: p.isBot }));
  core.sysSay(room, '词语揭晓：' + reveal.map((r) => `${r.nickname}「${r.word}」(${r.role === 'undercover' ? '卧底' : '平民'})`).join('；'));
  core.endGame(room, winner, reveal);
}

export const undercoverEngine = {
  type: 'undercover',
  name: '谁是卧底',
  icon: '🕵️',
  minPlayers: 4,
  maxPlayers: 8,
  defaultPlayers: 6,
  welcome: LINES.welcome,

  onStart(room) {
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
    say(room, 'start');
    for (const p of room.players) {
      if (!p.isBot) core.tell(room, p.userId, 'word', { word: p.word, tip: '描述它，但别说出它！' });
    }
    beginDescribe(room);
  },

  onSpeak(room, p, text) {
    if (room.phase !== 'speak') throw bad('现在不是描述阶段');
    if (room.turnSeat !== p.seat) throw bad('还没轮到你哦，听听别人怎么说～');
    if (p.word && text.includes(p.word)) throw bad('描述里不能直接说出你的词哦！');
    core.pushMsg(room, { userId: p.userId, nickname: p.nickname, kind: 'speak', content: text.slice(0, 100) });
    room.spoken.add(p.seat);
    nextTurn(room);
  },

  onVote(room, p, seat) { cast(room, p, seat); },

  onLeave(room, p) {
    if (room.status !== 'playing') return;
    if (checkWin(room)) return;
    if (room.phase === 'speak' && room.turnSeat === p.seat) nextTurn(room);
    if (room.phase === 'vote' && room.votes.size >= core.aliveSeats(room).length) settle(room, false);
  },

  decorateState(room, state, userId, me) {
    return {
      ...state,
      my_word: room.status === 'playing' && me ? me.word : null
    };
  }
};
