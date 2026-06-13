// ============================================================
// 迷雾庄园 · 凶夜（多人恐怖社交推理）
// ------------------------------------------------------------
// 一群人被困雾夜庄园，其中藏着「凶手」。每夜：凶手猎杀 → 通灵者感应
// → 守夜人守护；天亮公布死讯并抽取一张「灵异事件」（不确定性/随机性
// 的来源，借鉴恐怖片与 Phasmophobia 的氛围与误导），白天讨论 → 投票
// 驱逐疑凶。撑过 N 夜=救援抵达幸存者胜；凶手清场则凶手胜。
// 耐玩性：身份随机 + 事件牌库随机 + 线索不可靠（庄园会说谎）→ 局局不同。
// 公平铁律：身份纯随机；夜晚行动走私有通道；皮肤不可见于引擎。
// ============================================================
import { now, pick, randInt, shuffle } from '../lib/util.js';
import { bad } from '../lib/httpx.js';
import * as core from './core.js';

const ROLE_META = {
  killer: { name: '凶手', icon: '🔪', camp: 'killer', campLabel: '凶手阵营', campColor: '#c2532f', teammateLabel: '🔪 你的同伙', tip: '每夜猎杀一名幸存者。白天伪装无辜，别让大家投出你——也别被通灵者识破。' },
  medium: { name: '通灵者', icon: '🔮', camp: 'survivor', campLabel: '幸存者阵营', campColor: '#6b5cc8', teammateLabel: '', tip: '每夜感应一人的气息，但庄园偶尔会说谎——线索不一定可靠，用它带队却别全信。' },
  guard: { name: '守夜人', icon: '🛡', camp: 'survivor', campLabel: '幸存者阵营', campColor: '#2a9d76', teammateLabel: '', tip: '每夜守护一人，挡下凶手的猎杀（不能连续两夜守同一人）。猜对节奏是关键。' },
  survivor: { name: '幸存者', icon: '🕯', camp: 'survivor', campLabel: '幸存者阵营', campColor: '#2a9d76', teammateLabel: '', tip: '你没有特殊能力，但你的观察与投票决定庄园的命运。撑到黎明！' }
};

const LINES = {
  welcome: ['欢迎来到「迷雾庄园 · 凶夜」🕯 我是 AI 主持人句灵主持官。人齐后房主点开始——但愿你能活着看到黎明。', '雾，漫进了庄园的每一道门缝。今夜注定无人安眠……AI 主持人就位，随时开局。'],
  night: ['🌙 入夜了。请所有人闭上眼睛，把恐惧交给黑暗——凶手，请睁眼。', '烛火接连熄灭，庄园沉入死寂。天黑请闭眼，凶手开始行动……'],
  seance: ['🔮 凶手请闭眼。通灵者请睁眼，你想感应谁的气息？', '一缕阴风拂过，通灵者睁开了眼——今夜，你要触碰谁的灵魂？'],
  guard: ['🛡 通灵者请闭眼。守夜人请睁眼，今夜你要守护谁？', '守夜人握紧了手中的灯，准备彻夜守护一个人……'],
  dawnPeace: ['☀️ 天亮了。万幸，昨夜无人遇害——但雾，更浓了。', '晨光刺破浓雾，所有人都还活着。可那股寒意，并未散去……'],
  dawnDeath: ['☀️ 天亮了。{names} 倒在了冰冷的回廊里，再没能醒来……', '当第一缕光照进庄园，人们发现 {names} 已经没了气息。'],
  speak: ['活下来的人们，开始交换昨夜的见闻吧。谁在说谎？', '讨论开始。每一句证词背后，也许都藏着一把刀。'],
  turn: ['轮到 {name} 陈述（45 秒）', '{name}，说说你昨夜听见、看见了什么——'],
  voteStart: ['天黑前必须做出决定：把谁逐出庄园？投票吧。', '投票时刻。逐错了人，今夜也许就轮到你。'],
  tie: ['票数僵持，没有人被逐出——而夜，又要来了。', '众人面面相觑，谁也无法定罪。庄园的门，再次锁上。'],
  out: ['{name} 被众人逐入浓雾，TA 的身份是——{role}{icon}', '{name} 被推出了庄园大门，身份揭晓：{role}{icon}'],
  survivorWin: ['🌅 黎明的救援抵达，凶手再无藏身之处——幸存者们撑到了最后！', '警笛划破雾气，活下来的人们相拥而泣。这一夜，他们赢了。'],
  killerWin: ['🔪 庄园重归死寂，再没有人能阻止凶手……凶手胜利。', '最后一盏灯熄灭了。雾散时，只剩凶手的脚步声。'],
  botSpeak: ['昨晚我好像听见了脚步声，但不敢开门……', '我觉得 TA 的眼神不太对劲', '我整夜没睡，我是清白的！', '先别急着投票，再听听', '通灵者快出来带队啊', '我总觉得有人在撒谎', '这庄园太邪门了，我们得冷静', '我守着门一夜，什么也没发生']
};

// 灵异事件牌库：不确定性 / 随机性 / 误导 的来源（多数为氛围与红鲱鱼，少数给模糊真线索）
const EVENTS = [
  { key: 'calm', minRound: 1, lines: ['短暂的平静，连风都停了。但平静往往是更深的不安。', '这一夜出奇地安静，安静得让人发毛。'] },
  { key: 'coldspot', minRound: 1, lines: ['走廊尽头骤然阴冷，呵气成霜——有什么正盯着你们。', '温度毫无征兆地骤降，墙上的画像仿佛在转动。'] },
  { key: 'wail', minRound: 1, lines: ['一声凄厉的尖叫从阁楼传来，戛然而止。没人敢上去看。', '半夜，所有人都被一阵哭嚎惊醒，却找不到声音的来源。'] },
  { key: 'bloodstain', minRound: 1, effect: 'redherring', lines: ['一行血手印蜿蜒爬过地板，停在了 {who} 的房门前……（也许只是恶作剧）', '晨光下，血迹诡异地指向了 {who}——可这真的是线索吗？'] },
  { key: 'doll', minRound: 1, effect: 'doll', lines: ['{who} 的枕边出现了一只浑身湿透的玩偶，整夜噩梦缠身。', '诅咒玩偶选中了 {who}，TA 脸色惨白，久久说不出话。'] },
  { key: 'whisper', minRound: 2, effect: 'whisper', lines: ['风里传来断续的低语，仿佛在指认什么……', '通灵的余韵未散，一丝声音钻进众人耳中——'] },
  { key: 'blackout', minRound: 2, effect: 'blackout', lines: ['全庄园骤然停电，浓雾涌入。明夜，通灵者将什么也感应不到。', '灯火尽灭，黑暗吞没一切——明晚的感应，怕是要落空了。'] },
  { key: 'mirror', minRound: 3, effect: 'count', lines: ['古镜中浮现出扭曲的倒影，似乎在暗示着什么……', '镜面泛起血色涟漪，映出了庄园残存的恶意——'] }
];

const fmt = (tpl, vars = {}) => tpl.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
const say = (room, key, vars) => core.hostSay(room, fmt(pick(LINES[key]), vars));
const roleLabel = (p) => `${ROLE_META[p.role].name}${ROLE_META[p.role].icon}`;
const aliveKillers = (room) => core.alivePlayers(room).filter((p) => p.role === 'killer');
const findRole = (room, role) => room.players.find((p) => p.role === role);

// ---- 夜晚：猎杀 → 感应 → 守护 ----
function beginNight(room) {
  core.clearTimers(room);
  room.phase = 'night';
  room.stage = 'hunt';
  room.turnSeat = null;
  room.votes = new Map();
  const g = room.g;
  g.killPicks = new Map();
  g.victim = null;
  g.guardTarget = null;
  g.mediumDone = false;
  g.guardDone = false;
  room.phaseEndsAt = now() + 40_000;
  say(room, 'night');
  core.broadcast(room);
  for (const k of aliveKillers(room)) {
    if (k.isBot) {
      core.addTimer(room, randInt(2000, 6000), () => {
        if (room.stage !== 'hunt' || g.killPicks.has(k.seat)) return;
        const targets = core.alivePlayers(room).filter((p) => p.role !== 'killer');
        if (targets.length) doKillPick(room, k, pick(targets).seat);
      });
    } else {
      core.tell(room, k.userId, 'night', nightPromptFor(room, k));
    }
  }
  core.addTimer(room, 40_000, () => resolveHunt(room));
}

function doKillPick(room, p, targetSeat) {
  const g = room.g;
  g.killPicks.set(p.seat, targetSeat);
  const target = room.players.find((x) => x.seat === targetSeat);
  for (const k of aliveKillers(room).filter((x) => !x.isBot)) {
    core.tell(room, k.userId, 'accomplice_chat', { text: `${p.nickname} 想对 ${target.nickname} 下手（${g.killPicks.size}/${aliveKillers(room).length}）` });
  }
  if (g.killPicks.size >= aliveKillers(room).length) resolveHunt(room);
}

function resolveHunt(room) {
  if (room.stage !== 'hunt') return;
  core.clearTimers(room);
  const g = room.g;
  const counts = new Map();
  for (const t of g.killPicks.values()) counts.set(t, (counts.get(t) || 0) + 1);
  let best = null; let max = 0;
  for (const [seat, c] of counts) if (c > max || (c === max && Math.random() < 0.5)) { max = c; best = seat; }
  g.victim = best;
  beginSeance(room);
}

function beginSeance(room) {
  room.stage = 'seance';
  room.phaseEndsAt = now() + 25_000;
  say(room, 'seance');
  core.broadcast(room);
  const medium = findRole(room, 'medium');
  if (!medium?.alive) { core.addTimer(room, randInt(6000, 12_000), () => beginGuard(room)); return; }
  if (medium.isBot) {
    core.addTimer(room, randInt(2000, 6000), () => {
      if (room.stage !== 'seance' || room.g.mediumDone) return;
      room.g.mediumDone = true;
      beginGuard(room);
    });
  } else {
    core.tell(room, medium.userId, 'night', nightPromptFor(room, medium));
  }
  core.addTimer(room, 25_000, () => { if (room.stage === 'seance') beginGuard(room); });
}

function beginGuard(room) {
  if (room.stage === 'guard') return;
  core.clearTimers(room);
  room.stage = 'guard';
  room.phaseEndsAt = now() + 25_000;
  say(room, 'guard');
  core.broadcast(room);
  const g = room.g;
  const guard = findRole(room, 'guard');
  if (!guard?.alive) { core.addTimer(room, randInt(6000, 12_000), () => resolveNight(room)); return; }
  if (guard.isBot) {
    core.addTimer(room, randInt(2000, 6000), () => {
      if (room.stage !== 'guard' || g.guardDone) return;
      const targets = core.alivePlayers(room).filter((p) => p.seat !== g.lastGuard);
      if (targets.length) { g.guardTarget = pick(targets).seat; g.lastGuard = g.guardTarget; }
      g.guardDone = true;
      resolveNight(room);
    });
  } else {
    core.tell(room, guard.userId, 'night', nightPromptFor(room, guard));
  }
  core.addTimer(room, 25_000, () => resolveNight(room));
}

function resolveNight(room) {
  if (room.phase !== 'night') return;
  core.clearTimers(room);
  room.stage = null;
  const g = room.g;
  const deaths = [];
  if (g.victim != null && g.victim !== g.guardTarget) {
    const v = room.players.find((p) => p.seat === g.victim);
    if (v?.alive) deaths.push(v);
  }
  for (const d of deaths) d.alive = false;
  if (deaths.length) {
    say(room, 'dawnDeath', { names: deaths.map((d) => d.nickname).join('、') });
    core.sysSay(room, deaths.map((d) => `${d.nickname} 的身份是 ${roleLabel(d)}`).join('；'));
  } else {
    say(room, 'dawnPeace');
    if (g.victim != null) core.sysSay(room, '守夜人的灯，照住了今夜的猎物。');
  }
  if (checkWin(room)) return;
  drawEvent(room);
  beginSpeak(room);
}

// ---- 灵异事件：随机抽取，制造不确定性与误导 ----
function drawEvent(room) {
  const g = room.g;
  const pool = EVENTS.filter((e) => room.round >= (e.minRound || 1) && e.key !== g.lastEvent);
  const ev = pick(pool.length ? pool : EVENTS);
  g.lastEvent = ev.key;
  const aliveOthers = core.alivePlayers(room);
  const who = aliveOthers.length ? pick(aliveOthers).nickname : '某人';
  core.hostSay(room, '【灵异事件】' + fmt(pick(ev.lines), { who }));

  if (ev.effect === 'whisper') {
    // 模糊真线索：揭示某存活者阵营，70% 可靠（30% 庄园说谎 → 不确定性）
    const target = pick(aliveOthers);
    const truthful = Math.random() < 0.7;
    const realEvil = target.role === 'killer';
    const shown = (truthful ? realEvil : !realEvil) ? '凶手的气息' : '清白的气息';
    core.sysSay(room, `低语提到了 ${target.nickname}……隐约是「${shown}」（未必可信）`);
  } else if (ev.effect === 'blackout') {
    g.blackout = true;   // 下一夜通灵者失效
  } else if (ev.effect === 'count') {
    core.sysSay(room, `镜中映出：庄园里还潜伏着 ${aliveKillers(room).length} 名凶手。`);
  }
  // redherring / doll / calm / coldspot / wail 仅氛围与误导，无机械影响
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
      core.sysSay(room, `${p.nickname} 沉默地度过了发言时间，自动过麦`);
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
      let targets = core.alivePlayers(room).filter((x) => x.seat !== p.seat);
      if (p.role === 'killer') {                       // 凶手机器人避开同伙
        const nonKiller = targets.filter((x) => x.role !== 'killer');
        if (nonKiller.length) targets = nonKiller;
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
  if (room.round >= (room.g.maxRounds || 6)) return finish(room, 'survivor', '当第一缕晨光刺破浓雾，远处传来了救援的引擎声——');
  room.round += 1;
  core.addTimer(room, 3000, () => beginNight(room));
  core.broadcast(room);
}

function checkWin(room) {
  const alive = core.alivePlayers(room);
  const killers = alive.filter((p) => p.role === 'killer').length;
  const survivors = alive.length - killers;
  if (killers === 0) { finish(room, 'survivor'); return true; }
  if (killers >= survivors) { finish(room, 'killer'); return true; }
  core.broadcast(room);
  return false;
}

function finish(room, winner, extra = '') {
  if (extra) core.sysSay(room, extra);
  say(room, winner === 'survivor' ? 'survivorWin' : 'killerWin');
  const reveal = room.players.map((p) => ({
    seat: p.seat, nickname: p.nickname, role: p.role,
    word: `${ROLE_META[p.role].name}${ROLE_META[p.role].icon}`, is_bot: p.isBot
  }));
  core.sysSay(room, '身份揭晓：' + reveal.map((r) => `${r.nickname} ${r.word}`).join('；'));
  core.endGame(room, winner, reveal);
}

// 夜晚私有提示（通用协议：title/targets/action/can_skip，供前端声明式渲染）
function nightPromptFor(room, p) {
  const g = room.g;
  if (!p.alive) return null;
  const others = core.alivePlayers(room).filter((x) => x.seat !== p.seat).map((x) => ({ seat: x.seat, nickname: x.nickname }));
  if (room.stage === 'hunt' && p.role === 'killer') {
    return {
      stage: 'hunt', acted: g.killPicks.has(p.seat), action: 'hunt', pick_label: '🔪 猎杀',
      title: '🔪 选择今夜的猎物',
      targets: core.alivePlayers(room).filter((x) => x.role !== 'killer').map((x) => ({ seat: x.seat, nickname: x.nickname })),
      teammates: aliveKillers(room).filter((k) => k.seat !== p.seat).map((k) => k.nickname),
      tip: '与同伙达成一致，选定一名幸存者'
    };
  }
  if (room.stage === 'seance' && p.role === 'medium') {
    if (g.blackout) return { stage: 'seance', acted: true, title: '🌫 浓雾弥漫，今夜什么也感应不到…', targets: [], action: 'sense' };
    return { stage: 'seance', acted: g.mediumDone, action: 'sense', pick_label: '🔮 感应', title: '🔮 感应谁的气息？（线索未必可靠）', targets: others, tip: '感应一人，但庄园偶尔说谎' };
  }
  if (room.stage === 'guard' && p.role === 'guard') {
    return {
      stage: 'guard', acted: g.guardDone, action: 'protect', pick_label: '🛡 守护',
      title: '🛡 今夜守护谁？',
      targets: others.filter((x) => x.seat !== g.lastGuard),
      can_skip: true,
      tip: '挡下凶手的猎杀（不能连守同一人）'
    };
  }
  return null;
}

export const horrorEngine = {
  type: 'horror',
  name: '迷雾庄园·凶夜',
  icon: '🕯',
  minPlayers: 5,
  maxPlayers: 10,
  defaultPlayers: 6,
  welcome: LINES.welcome,

  onStart(room) {
    const n = room.players.length;
    const killerCount = n >= 9 ? 2 : 1;
    const seats = shuffle(room.players.map((p) => p.seat));
    const killerSeats = new Set(seats.slice(0, killerCount));
    const mediumSeat = seats[killerCount];
    const guardSeat = seats[killerCount + 1];
    for (const p of room.players) {
      p.alive = true;
      p.role = killerSeats.has(p.seat) ? 'killer' : p.seat === mediumSeat ? 'medium' : p.seat === guardSeat ? 'guard' : 'survivor';
    }
    room.g = { mediumLog: {}, maxRounds: 6, lastGuard: null, lastEvent: null, blackout: false };
    core.hostSay(room, `本局：${killerCount} 凶手 · 1 通灵者 · 1 守夜人 · ${n - killerCount - 2} 幸存者。身份已私发。撑过 ${room.g.maxRounds} 夜即可等到救援——天黑请闭眼。`);
    for (const p of room.players.filter((x) => !x.isBot)) {
      const meta = ROLE_META[p.role];
      core.tell(room, p.userId, 'role', {
        role: p.role, name: meta.name, icon: meta.icon, camp: meta.camp,
        camp_label: meta.campLabel, camp_color: meta.campColor, teammate_label: meta.teammateLabel, tip: meta.tip,
        teammates: p.role === 'killer' ? room.players.filter((k) => k.role === 'killer' && k.seat !== p.seat).map((k) => k.nickname) : []
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

  // 夜晚行动：{action: hunt|sense|protect|skip, target_seat}
  onAction(room, p, body) {
    const g = room.g;
    const act = body.action;
    if (room.phase !== 'night') throw bad('现在不是夜晚行动时间');
    if (!p.alive) throw bad('你已出局');
    const target = body.target_seat != null ? room.players.find((x) => x.seat === Number(body.target_seat)) : null;

    if (act === 'hunt') {
      if (room.stage !== 'hunt' || p.role !== 'killer') throw bad('现在不能进行这个操作');
      if (g.killPicks.has(p.seat)) throw bad('你已经选择过了');
      if (!target?.alive || target.role === 'killer') throw bad('目标无效');
      doKillPick(room, p, target.seat);
      return { done: true, message: `已锁定猎物：${target.nickname}` };
    }
    if (act === 'sense') {
      if (room.stage !== 'seance' || p.role !== 'medium') throw bad('现在不能进行这个操作');
      if (g.mediumDone) throw bad('今夜已经感应过了');
      if (g.blackout) throw bad('浓雾太重，今夜无法感应');
      if (!target?.alive || target.seat === p.seat) throw bad('目标无效');
      g.mediumDone = true;
      // 75% 可靠，25% 庄园说谎 → 制造不确定性
      const truthful = Math.random() < 0.75;
      const realEvil = target.role === 'killer';
      const result = (truthful ? realEvil : !realEvil) ? '凶手的气息 🔪' : '清白的气息 ✨';
      g.mediumLog[room.round] = `${target.nickname}：${result}`;
      core.tell(room, p.userId, 'sense_result', { nickname: target.nickname, result, round: room.round });
      core.addTimer(room, randInt(1500, 4000), () => beginGuard(room));
      return { done: true, result: `感应到 ${target.nickname} 散发着 ${result}` };
    }
    if (act === 'protect' || act === 'skip') {
      if (room.stage !== 'guard' || p.role !== 'guard') throw bad('现在不能进行这个操作');
      if (g.guardDone) throw bad('今夜已经行动过了');
      if (act === 'protect') {
        if (!target?.alive) throw bad('目标无效');
        if (target.seat === g.lastGuard) throw bad('不能连续两夜守护同一人');
        g.guardTarget = target.seat; g.lastGuard = target.seat;
      } else {
        g.lastGuard = null;
      }
      g.guardDone = true;
      core.addTimer(room, randInt(1000, 3000), () => resolveNight(room));
      return { done: true, message: act === 'protect' ? `今夜守护 ${target.nickname}` : '今夜不守护任何人' };
    }
    throw bad('未知操作');
  },

  onLeave(room, p) {
    if (room.status !== 'playing') return;
    if (checkWin(room)) return;
    if (room.phase === 'speak' && room.turnSeat === p.seat) nextTurn(room);
    if (room.phase === 'vote' && room.votes.size >= core.aliveSeats(room).length) settle(room, false);
    if (room.phase === 'night') {
      if (room.stage === 'hunt' && aliveKillers(room).every((k) => room.g.killPicks.has(k.seat))) resolveHunt(room);
      if (room.stage === 'seance' && p.role === 'medium') beginGuard(room);
      if (room.stage === 'guard' && p.role === 'guard') resolveNight(room);
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
        name: meta.name, icon: meta.icon, camp: meta.camp,
        camp_label: meta.campLabel, camp_color: meta.campColor, teammate_label: meta.teammateLabel, tip: meta.tip,
        teammates: me.role === 'killer' ? room.players.filter((k) => k.role === 'killer' && k.seat !== me.seat).map((k) => k.nickname) : [],
        clue_log: me.role === 'medium' ? room.g.mediumLog : null
      } : null,
      my_night: room.phase === 'night' ? nightPromptFor(room, me) : null
    };
  }
};
