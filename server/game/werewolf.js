// ============================================================
// 狼人杀（基础局）：狼人 / 预言家 / 女巫 / 平民
// 夜晚（狼人刀人 → 预言家查验 → 女巫救/毒）→ 白天（公布死讯 →
// 轮流发言 → 投票放逐）循环；屠边判负：狼数 ≥ 好人数 狼胜。
// 公平铁律：身份纯随机；夜晚行动走私有通道；皮肤不可见于引擎。
// ============================================================
import { now, pick, randInt, shuffle } from '../lib/util.js';
import { bad } from '../lib/httpx.js';
import * as core from './core.js';

const ROLE_META = {
  wolf: { name: '狼人', icon: '🐺', camp: 'wolf', tip: '每晚和队友商量刀掉一名玩家。白天伪装好人，别被投出去！' },
  seer: { name: '预言家', icon: '🔮', camp: 'good', tip: '每晚查验一名玩家的阵营。白天用信息带领好人，但小心暴露！' },
  witch: { name: '女巫', icon: '🧪', camp: 'good', tip: '你有一瓶解药和一瓶毒药（全局各一次）。同一晚只能用一瓶。' },
  villager: { name: '平民', icon: '🙂', camp: 'good', tip: '认真听发言，找出狼人，投票放逐！' }
};

const LINES = {
  welcome: ['欢迎来到「狼人杀」！我是 AI 主持人句灵主持官，人齐后房主点开始，天黑请闭眼～', '月圆之夜，狼影重重……AI 主持人就位，随时开局！'],
  night: ['天黑请闭眼 🌙 狼人请睁眼……', '夜幕降临，村庄陷入寂静。狼人们睁开了眼睛——'],
  seer: ['狼人请闭眼。预言家请睁眼，你要查验谁？🔮', '预言家缓缓睁眼，今晚想看清谁的真面目？'],
  witch: ['预言家请闭眼。女巫请睁眼 🧪', '女巫睁开眼睛，药瓶在月光下闪着微光……'],
  dawnPeace: ['天亮了 ☀️ 昨晚是平安夜，无人死亡！', '太阳升起，所有人都平安无事。今天会是好天气吗？'],
  dawnDeath: ['天亮了 ☀️ 昨晚，{names} 倒在了血泊中……', '清晨的钟声响起，村民发现 {names} 再也没有醒来。'],
  speak: ['请大家依次发言，分析昨晚的局势～', '发言阶段开始！是直球对线还是暗中观察，看你们的了。'],
  turn: ['轮到 {name} 发言（45 秒）', '{name}，请开始你的陈述——'],
  voteStart: ['发言结束，请投出你心中的狼人！', '投票时刻！每一票都可能改变村庄的命运。'],
  tie: ['平票！今天无人被放逐。', '票数僵持，村民们犹豫了……今天没有人离开。'],
  out: ['{name} 被放逐出局，TA 的身份是——{role}{icon}', '{name} 被村民投了出去，身份是：{role}{icon}'],
  goodWin: ['所有狼人被消灭，好人阵营胜利！🎉', '正义降临！狼人全部出局，好人胜利！'],
  wolfWin: ['狼人数量已不可阻挡……狼人阵营胜利！🐺', '夜色吞没了村庄，狼人获得了最终胜利！'],
  botSpeak: ['我昨晚睡得很沉，什么都不知道……', '我觉得刚才那位发言有点奇怪', '我是好人，真的！', '先听听后面的人怎么说', '我有点怀疑跳得快的人', '逻辑上讲，我暂时保持中立', '这局水好深，我先苟一下', '相信我一票，不亏的']
};
const fmt = (tpl, vars = {}) => tpl.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
const say = (room, key, vars) => core.hostSay(room, fmt(pick(LINES[key]), vars));
const roleLabel = (p) => `${ROLE_META[p.role].name}${ROLE_META[p.role].icon}`;

const aliveWolves = (room) => core.alivePlayers(room).filter((p) => p.role === 'wolf');
const findRole = (room, role) => room.players.find((p) => p.role === role);

// ---- 夜晚 ----
function beginNight(room) {
  core.clearTimers(room);
  room.phase = 'night';
  room.stage = 'wolf';
  room.turnSeat = null;
  room.votes = new Map();
  const g = room.g;
  g.wolfPicks = new Map();
  g.victim = null;
  g.saved = false;
  g.poisonTarget = null;
  g.seerDone = false;
  g.witchDone = false;
  room.phaseEndsAt = now() + 40_000;
  say(room, 'night');
  core.broadcast(room);
  for (const w of aliveWolves(room)) {
    if (w.isBot) {
      core.addTimer(room, randInt(2000, 6000), () => {
        if (room.stage !== 'wolf' || g.wolfPicks.has(w.seat)) return;
        const targets = core.alivePlayers(room).filter((p) => p.role !== 'wolf');
        if (targets.length) doWolfPick(room, w, pick(targets).seat);
      });
    } else {
      core.tell(room, w.userId, 'night', nightPromptFor(room, w));
    }
  }
  core.addTimer(room, 40_000, () => resolveWolf(room));
}

function doWolfPick(room, p, targetSeat) {
  const g = room.g;
  g.wolfPicks.set(p.seat, targetSeat);
  const target = room.players.find((x) => x.seat === targetSeat);
  // 狼频道：仅通知狼队友
  for (const w of aliveWolves(room).filter((x) => !x.isBot)) {
    core.tell(room, w.userId, 'wolf_chat', { text: `${p.nickname} 提议刀 ${target.nickname}（${g.wolfPicks.size}/${aliveWolves(room).length}）` });
  }
  if (g.wolfPicks.size >= aliveWolves(room).length) resolveWolf(room);
}

function resolveWolf(room) {
  if (room.stage !== 'wolf') return;
  core.clearTimers(room);
  const g = room.g;
  const counts = new Map();
  for (const t of g.wolfPicks.values()) counts.set(t, (counts.get(t) || 0) + 1);
  let best = null; let max = 0;
  for (const [seat, c] of counts) if (c > max || (c === max && Math.random() < 0.5)) { max = c; best = seat; }
  g.victim = best;          // 可能为 null（狼人空刀/超时）
  beginSeer(room);
}

function beginSeer(room) {
  room.stage = 'seer';
  room.phaseEndsAt = now() + 25_000;
  say(room, 'seer');
  core.broadcast(room);
  const seer = findRole(room, 'seer');
  if (!seer?.alive) {
    // 预言家已死：留满悬念时间防止身份被时长推断
    core.addTimer(room, randInt(6000, 12_000), () => beginWitch(room));
    return;
  }
  if (seer.isBot) {
    core.addTimer(room, randInt(2000, 6000), () => {
      if (room.stage !== 'seer' || room.g.seerDone) return;
      const targets = core.alivePlayers(room).filter((p) => p.seat !== seer.seat);
      room.g.seerDone = true;
      void targets;          // 机器人查验结果无需通知
      beginWitch(room);
    });
  } else {
    core.tell(room, seer.userId, 'night', nightPromptFor(room, seer));
  }
  core.addTimer(room, 25_000, () => { if (room.stage === 'seer') beginWitch(room); });
}

function beginWitch(room) {
  if (room.stage === 'witch') return;
  core.clearTimers(room);
  room.stage = 'witch';
  room.phaseEndsAt = now() + 25_000;
  say(room, 'witch');
  core.broadcast(room);
  const g = room.g;
  const witch = findRole(room, 'witch');
  if (!witch?.alive) {
    core.addTimer(room, randInt(6000, 12_000), () => resolveNight(room));
    return;
  }
  if (witch.isBot) {
    core.addTimer(room, randInt(2000, 6000), () => {
      if (room.stage !== 'witch' || g.witchDone) return;
      // 机器人女巫：有解药且有人被刀 → 60% 救；否则 12% 随机毒
      if (!g.saveUsed && g.victim != null && Math.random() < 0.6) {
        g.saved = true; g.saveUsed = true;
      } else if (!g.poisonUsed && Math.random() < 0.12) {
        const targets = core.alivePlayers(room).filter((p) => p.seat !== witch.seat);
        if (targets.length) { g.poisonTarget = pick(targets).seat; g.poisonUsed = true; }
      }
      g.witchDone = true;
      resolveNight(room);
    });
  } else {
    core.tell(room, witch.userId, 'night', nightPromptFor(room, witch));
  }
  core.addTimer(room, 25_000, () => resolveNight(room));
}

function resolveNight(room) {
  if (room.phase !== 'night') return;
  core.clearTimers(room);
  room.stage = null;
  const g = room.g;
  const deaths = [];
  if (g.victim != null && !g.saved) {
    const v = room.players.find((p) => p.seat === g.victim);
    if (v?.alive) deaths.push(v);
  }
  if (g.poisonTarget != null) {
    const t = room.players.find((p) => p.seat === g.poisonTarget);
    if (t?.alive && !deaths.includes(t)) deaths.push(t);
  }
  for (const d of deaths) d.alive = false;
  if (deaths.length) {
    say(room, 'dawnDeath', { names: deaths.map((d) => d.nickname).join('、') });
    core.sysSay(room, deaths.map((d) => `${d.nickname} 的身份是 ${roleLabel(d)}`).join('；'));
  } else {
    say(room, 'dawnPeace');
  }
  if (checkWin(room)) return;
  beginSpeak(room);
}

// ---- 白天 ----
function beginSpeak(room) {
  room.phase = 'speak';
  room.stage = null;
  room.spoken = new Set();
  room.votes = new Map();
  say(room, 'speak');
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
    room.phaseEndsAt = now() + 45_000;
    say(room, 'turn', { name: p.nickname });
    core.broadcast(room);
    core.addTimer(room, 45_000, () => {
      core.sysSay(room, `${p.nickname} 超时未发言，自动过麦`);
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
      // 机器人狼人避开队友
      let targets = core.alivePlayers(room).filter((x) => x.seat !== p.seat);
      if (p.role === 'wolf') {
        const nonWolf = targets.filter((x) => x.role !== 'wolf');
        if (nonWolf.length) targets = nonWolf;
      }
      cast(room, p, pick(targets).seat);
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
  if (out) {
    out.alive = false;
    say(room, 'out', { name: out.nickname, role: ROLE_META[out.role].name, icon: ROLE_META[out.role].icon });
    if (checkWin(room)) return;
  } else {
    say(room, 'tie');
  }
  if (room.round >= 8) return finish(room, 'wolf', '夜太长了，村庄沦陷……');
  room.round += 1;
  core.addTimer(room, 3000, () => beginNight(room));
  core.broadcast(room);
}

function checkWin(room) {
  const alive = core.alivePlayers(room);
  const wolves = alive.filter((p) => p.role === 'wolf').length;
  if (wolves === 0) { finish(room, 'good'); return true; }
  if (wolves >= alive.length - wolves) { finish(room, 'wolf'); return true; }
  core.broadcast(room);
  return false;
}

function finish(room, winner, extra = '') {
  if (extra) core.sysSay(room, extra);
  say(room, winner === 'good' ? 'goodWin' : 'wolfWin');
  const reveal = room.players.map((p) => ({
    seat: p.seat, nickname: p.nickname, role: p.role,
    word: `${ROLE_META[p.role].name}${ROLE_META[p.role].icon}`, is_bot: p.isBot
  }));
  core.sysSay(room, '身份揭晓：' + reveal.map((r) => `${r.nickname} ${r.word}`).join('；'));
  core.endGame(room, winner, reveal);
}

// 夜晚私有提示（含重连恢复）
function nightPromptFor(room, p) {
  const g = room.g;
  const targets = core.alivePlayers(room).filter((x) => x.seat !== p.seat).map((x) => ({ seat: x.seat, nickname: x.nickname }));
  if (room.stage === 'wolf' && p.role === 'wolf' && p.alive) {
    return {
      stage: 'wolf', acted: g.wolfPicks.has(p.seat),
      targets: core.alivePlayers(room).filter((x) => x.role !== 'wolf').map((x) => ({ seat: x.seat, nickname: x.nickname })),
      teammates: aliveWolves(room).filter((w) => w.seat !== p.seat).map((w) => w.nickname),
      tip: '和队友达成一致，选择今晚的目标'
    };
  }
  if (room.stage === 'seer' && p.role === 'seer' && p.alive) {
    return { stage: 'seer', acted: g.seerDone, targets, tip: '选择一名玩家查验阵营' };
  }
  if (room.stage === 'witch' && p.role === 'witch' && p.alive) {
    const victim = g.victim != null && !g.saved ? room.players.find((x) => x.seat === g.victim) : null;
    return {
      stage: 'witch', acted: g.witchDone,
      victim: victim ? { seat: victim.seat, nickname: victim.nickname } : null,
      can_save: !g.saveUsed && !!victim,
      can_poison: !g.poisonUsed,
      targets, tip: '同一晚只能用一瓶药'
    };
  }
  return null;
}

export const werewolfEngine = {
  type: 'werewolf',
  name: '狼人杀',
  icon: '🐺',
  minPlayers: 6,
  maxPlayers: 12,
  defaultPlayers: 8,
  welcome: LINES.welcome,

  onStart(room) {
    const n = room.players.length;
    const wolfCount = n >= 9 ? 3 : 2;
    const seats = shuffle(room.players.map((p) => p.seat));
    const wolfSeats = new Set(seats.slice(0, wolfCount));
    const seerSeat = seats[wolfCount];
    const witchSeat = seats[wolfCount + 1];
    for (const p of room.players) {
      p.alive = true;
      p.role = wolfSeats.has(p.seat) ? 'wolf' : p.seat === seerSeat ? 'seer' : p.seat === witchSeat ? 'witch' : 'villager';
    }
    room.g = { saveUsed: false, poisonUsed: false, seerLog: {} };
    core.hostSay(room, `本局配置：${wolfCount} 狼人 · 1 预言家 · 1 女巫 · ${n - wolfCount - 2} 平民。身份已私发，天黑请闭眼！`);
    for (const p of room.players.filter((x) => !x.isBot)) {
      const meta = ROLE_META[p.role];
      core.tell(room, p.userId, 'role', {
        role: p.role, name: meta.name, icon: meta.icon, camp: meta.camp, tip: meta.tip,
        teammates: p.role === 'wolf' ? room.players.filter((w) => w.role === 'wolf' && w.seat !== p.seat).map((w) => w.nickname) : []
      });
    }
    core.addTimer(room, 2500, () => beginNight(room));
    core.broadcast(room);
  },

  onSpeak(room, p, text) {
    if (room.phase !== 'speak') throw bad('现在不是发言阶段');
    if (room.turnSeat !== p.seat) throw bad('还没轮到你发言哦');
    core.pushMsg(room, { userId: p.userId, nickname: p.nickname, kind: 'speak', content: text.slice(0, 120) });
    room.spoken.add(p.seat);
    nextTurn(room);
  },

  onVote(room, p, seat) { cast(room, p, seat); },

  /**
   * 夜晚行动：{action: kill|check|save|poison|skip, target_seat}
   * 返回值会作为接口响应（如查验结果只给预言家本人）
   */
  onAction(room, p, body) {
    const g = room.g;
    const act = body.action;
    if (room.phase !== 'night') throw bad('现在不是行动时间');
    if (!p.alive) throw bad('你已出局');
    const target = body.target_seat != null ? room.players.find((x) => x.seat === Number(body.target_seat)) : null;

    if (act === 'kill') {
      if (room.stage !== 'wolf' || p.role !== 'wolf') throw bad('现在不能进行这个操作');
      if (g.wolfPicks.has(p.seat)) throw bad('你已经选择过了');
      if (!target?.alive || target.seat === p.seat) throw bad('目标无效');
      doWolfPick(room, p, target.seat);
      return { done: true, message: `已提议刀 ${target.nickname}` };
    }
    if (act === 'check') {
      if (room.stage !== 'seer' || p.role !== 'seer') throw bad('现在不能进行这个操作');
      if (g.seerDone) throw bad('今晚已经查验过了');
      if (!target?.alive || target.seat === p.seat) throw bad('目标无效');
      g.seerDone = true;
      const result = target.role === 'wolf' ? '狼人 🐺' : '好人 ✨';
      g.seerLog[room.round] = `${target.nickname}：${result}`;
      core.tell(room, p.userId, 'seer_result', { nickname: target.nickname, result });
      core.addTimer(room, randInt(1500, 4000), () => beginWitch(room));
      return { done: true, result: `${target.nickname} 的身份是 ${result}` };
    }
    if (act === 'save' || act === 'poison' || act === 'skip') {
      if (room.stage !== 'witch' || p.role !== 'witch') throw bad('现在不能进行这个操作');
      if (g.witchDone) throw bad('今晚已经行动过了');
      if (act === 'save') {
        if (g.saveUsed) throw bad('解药已经用过了');
        if (g.victim == null) throw bad('今晚没有人需要解救');
        g.saved = true; g.saveUsed = true;
      } else if (act === 'poison') {
        if (g.poisonUsed) throw bad('毒药已经用过了');
        if (!target?.alive || target.seat === p.seat) throw bad('目标无效');
        g.poisonTarget = target.seat; g.poisonUsed = true;
      }
      g.witchDone = true;
      core.addTimer(room, randInt(1000, 3000), () => resolveNight(room));
      return { done: true, message: act === 'save' ? '解药已使用' : act === 'poison' ? '毒药已使用' : '今晚按兵不动' };
    }
    throw bad('未知操作');
  },

  onLeave(room, p) {
    if (room.status !== 'playing') return;
    if (checkWin(room)) return;
    if (room.phase === 'speak' && room.turnSeat === p.seat) nextTurn(room);
    if (room.phase === 'vote' && room.votes.size >= core.aliveSeats(room).length) settle(room, false);
    if (room.phase === 'night') {
      if (room.stage === 'wolf' && aliveWolves(room).every((w) => room.g.wolfPicks.has(w.seat))) resolveWolf(room);
      if (room.stage === 'seer' && p.role === 'seer') beginWitch(room);
      if (room.stage === 'witch' && p.role === 'witch') resolveNight(room);
    }
  },

  decorateState(room, state, userId, me) {
    if (!me || room.status !== 'playing') {
      return { ...state, my_role: room.status === 'ended' && me ? me.role : null };
    }
    const meta = me.role ? ROLE_META[me.role] : null;
    return {
      ...state,
      my_role: me.role,
      my_role_info: meta ? {
        name: meta.name, icon: meta.icon, camp: meta.camp, tip: meta.tip,
        teammates: me.role === 'wolf' ? room.players.filter((w) => w.role === 'wolf' && w.seat !== me.seat).map((w) => w.nickname) : [],
        potions: me.role === 'witch' ? { save: !room.g.saveUsed, poison: !room.g.poisonUsed } : null,
        seer_log: me.role === 'seer' ? room.g.seerLog : null
      } : null,
      my_night: room.phase === 'night' ? nightPromptFor(room, me) : null
    };
  }
};
