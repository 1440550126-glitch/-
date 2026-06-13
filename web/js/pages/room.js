// 游戏房间：座位 / 准备 / AI 主持 / 发言 / 投票 / 夜间行动（狼人杀）/ 结算
import { GET, POST, sse } from '../api.js';
import { h, toast, avatarEl, sheet, confirmSheet } from '../ui.js';
import { store, skinPayload } from '../store.js';
import { nav } from '../router.js';
import { reportSheet } from './feed.js';

export async function renderRoom(page, params) {
  const roomId = params.id;
  let data;
  try { data = await GET(`/api/rooms/${roomId}`); }
  catch (e) { toast(e.message, 'warn'); nav('/games'); return; }

  let room = data.room;
  let myWord = room.my_word || null;
  let myRole = room.my_role_info ? { role: room.my_role, ...room.my_role_info } : null;
  let myNight = room.my_night || null;
  let seerLog = myRole?.seer_log || {};
  const myId = store.me?.id;
  const isWolfGame = room.game_type === 'werewolf';
  const isHorror = room.game_type === 'horror';

  // 房主装备的房间主题皮肤（纯外观换肤）
  const theme = room.theme ? skinPayload(room.theme) : null;
  if (theme?.bg) {
    page.style.background = `linear-gradient(165deg, ${theme.bg[0]}, ${theme.bg[1]})`;
    page.style.color = '#f3eefc';
  }

  const titleEl = h('h1', { style: { fontSize: '17px' } }, room.name);
  const phaseEl = h('div', { class: 'sub', style: theme ? { color: 'rgba(255,255,255,.6)' } : {} }, '');
  const seatsEl = h('div', { class: 'seats' });
  const infoSlot = h('div', {});       // 词卡 / 身份卡 / 结算
  const nightSlot = h('div', {});      // 夜间行动面板
  const chatBox = h('div', { class: 'chat-box' });
  const actionSlot = h('div', { style: { marginTop: '10px' } });
  const timerEl = h('span', { style: { fontSize: '11px', color: 'var(--brand)', fontWeight: 700 } });

  const chatWrap = h('div', { class: 'glass card', style: { maxHeight: '34vh', overflowY: 'auto', background: theme ? 'rgba(255,255,255,.92)' : undefined } }, chatBox);

  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => leave(false) }, '←'),
      h('div', {}, titleEl, phaseEl),
      h('div', { class: 'spacer' }),
      timerEl,
      h('button', { class: 'icon-btn', onclick: menuSheet }, '⋯')
    ),
    h('div', { class: 'glass card', style: { background: theme ? 'rgba(255,255,255,.9)' : undefined } },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--ink-2)' } },
        theme?.emoji ? h('span', { style: { fontSize: '16px' } }, theme.emoji) : (isHorror ? '🕯' : isWolfGame ? '🐺' : '🕵️'),
        `${room.game_name || (isHorror ? '迷雾庄园·凶夜' : isWolfGame ? '狼人杀' : '谁是卧底')} · 房间号 ${room.id}`,
        h('span', { class: 'badge-ai' }, '🤖 AI 主持')),
      seatsEl,
      infoSlot,
      nightSlot
    ),
    chatWrap,
    actionSlot
  );

  const timerInt = setInterval(() => {
    if (room.phase_ends_at) {
      const left = Math.max(0, Math.ceil((room.phase_ends_at - Date.now()) / 1000));
      timerEl.textContent = left > 0 ? `⏱ ${left}s` : '';
    } else timerEl.textContent = '';
  }, 500);

  function phaseName() {
    if (room.status === 'waiting') return '等待开始';
    if (room.status === 'ended') return '已结束';
    if (room.phase === 'night') {
      return `第 ${room.round} 夜 · ${{ wolf: '狼人行动中', seer: '预言家行动中', witch: '女巫行动中', hunt: '凶手潜行中', seance: '通灵者感应中', guard: '守夜人守护中' }[room.stage] || '夜晚'}`;
    }
    return { speak: `第 ${room.round} 轮 · 发言`, vote: `第 ${room.round} 轮 · 投票` }[room.phase] || '';
  }

  function renderSeats() {
    seatsEl.innerHTML = '';
    phaseEl.textContent = phaseName();
    const me = room.players.find((p) => p.user_id === myId);
    const iVoted = me?.voted;
    for (const p of room.players) {
      const isTurn = room.phase === 'speak' && room.turn_seat === p.seat;
      const canVote = room.status === 'playing' && room.phase === 'vote' && me?.alive && !iVoted && p.alive && p.user_id !== myId;
      seatsEl.append(h('div', { class: `seat filled ${isTurn ? 'turn' : ''} ${p.alive === false ? 'dead' : ''}` },
        avatarEl({ avatar: p.avatar }, 34),
        h('div', { class: 's-name' }, p.nickname),
        p.is_bot ? h('span', { class: 's-tag' }, '🤖 ' + p.ai_label) :
          room.status === 'waiting'
            ? h('span', { class: 's-tag', style: p.ready ? { background: 'rgba(98,217,181,.18)', color: '#2a9d76' } : {} }, p.ready ? '已准备' : '等待中')
            : p.user_id === room.host_id ? h('span', { class: 's-tag' }, '房主') : null,
        room.phase === 'vote' && p.voted && p.alive ? h('span', { class: 's-tag' }, '已投') : null,
        canVote ? h('button', {
          class: 's-vote-btn',
          onclick: async () => {
            try { await POST(`/api/rooms/${roomId}/vote`, { target_seat: p.seat }); toast(`已投给 ${p.nickname}`); }
            catch (e) { toast(e.message, 'warn'); }
          }
        }) : null
      ));
    }
    for (let i = room.players.length; i < room.max_players; i++) {
      seatsEl.append(h('div', { class: 'seat' }, h('span', { style: { fontSize: '18px', opacity: 0.3 } }, '＋'), h('div', { class: 's-name' }, '虚位以待')));
    }
  }

  function renderInfo() {
    infoSlot.innerHTML = '';
    if (room.status === 'playing' && myWord) {
      infoSlot.append(h('div', { class: 'word-card' },
        h('div', { style: { fontSize: '10.5px', color: 'var(--ink-3)', marginBottom: '4px' } }, '你的词（只有你能看到）'),
        h('div', { class: 'w-word' }, myWord),
        h('div', { style: { fontSize: '10.5px', color: 'var(--ink-3)', marginTop: '4px' } }, '描述它，但别说出它！')
      ));
    }
    if (room.status === 'playing' && myRole) {
      const campColor = myRole.camp_color || (myRole.camp === 'wolf' ? '#c2532f' : '#2a9d76');
      const campLabel = myRole.camp_label || (myRole.camp === 'wolf' ? '狼人阵营' : '好人阵营');
      const teammateLabel = myRole.teammate_label || '🐺 你的队友';
      const clueLog = myRole.clue_log || {};
      infoSlot.append(h('div', { class: 'word-card' },
        h('div', { style: { fontSize: '10.5px', color: 'var(--ink-3)', marginBottom: '4px' } }, '你的身份（只有你能看到）'),
        h('div', { class: 'w-word' }, `${myRole.icon} ${myRole.name}`),
        h('div', { style: { fontSize: '11px', color: campColor, marginTop: '4px', fontWeight: 700 } }, campLabel),
        h('div', { style: { fontSize: '10.5px', color: 'var(--ink-3)', marginTop: '5px', lineHeight: 1.6 } }, myRole.tip),
        myRole.teammates?.length ? h('div', { style: { fontSize: '11px', color: campColor, marginTop: '5px' } }, `${teammateLabel}：${myRole.teammates.join('、')}`) : null,
        myRole.potions ? h('div', { style: { fontSize: '11px', marginTop: '5px' } }, `💊 解药${myRole.potions.save ? '×1' : '已用'} · ☠️ 毒药${myRole.potions.poison ? '×1' : '已用'}`) : null,
        Object.keys(seerLog).length ? h('div', { style: { fontSize: '11px', marginTop: '5px', color: 'var(--brand)' } },
          '🔮 查验记录：' + Object.entries(seerLog).map(([r, t]) => `第${r}夜 ${t}`).join('；')) : null,
        Object.keys(clueLog).length ? h('div', { style: { fontSize: '11px', marginTop: '5px', color: 'var(--brand)' } },
          '🔮 感应记录：' + Object.entries(clueLog).map(([r, t]) => `第${r}夜 ${t}`).join('；')) : null
      ));
    }
    if (room.status === 'ended' && room.reveal) {
      const winText = isHorror
        ? (room.winner === 'survivor' ? '🌅 幸存者撑到了黎明，胜利！' : '🔪 凶手笑到了最后……')
        : isWolfGame
          ? (room.winner === 'good' ? '🎉 好人阵营胜利！' : '🐺 狼人阵营胜利！')
          : (room.winner === 'civilian' ? '🎉 平民阵营胜利！' : '🕶️ 卧底阵营胜利！');
      infoSlot.append(h('div', { class: 'word-card' },
        h('div', { style: { fontWeight: 800, fontSize: '17px', marginBottom: '8px' } }, winText),
        h('div', { style: { fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.9 } },
          room.reveal.map((r) => `${r.nickname}「${r.word}」`).join('　'))
      ));
    }
  }

  // ---- 夜间行动面板（狼人杀） ----
  let poisonPicking = false;
  function renderNight() {
    nightSlot.innerHTML = '';
    if (room.phase !== 'night') { poisonPicking = false; return; }
    const banner = h('div', { style: { textAlign: 'center', fontSize: '12px', color: 'var(--ink-2)', padding: '8px 0 2px' } },
      '🌙 ' + ({ wolf: '夜深了，狼人正在行动…', seer: '预言家正在观星…', witch: '女巫打开了药箱…', hunt: '凶手在黑暗中游荡…', seance: '通灵者正在感应气息…', guard: '守夜人提灯巡视…' }[room.stage] || '天黑请闭眼'));
    nightSlot.append(banner);
    if (!myNight || myNight.stage !== room.stage) return;
    if (myNight.acted) {
      nightSlot.append(h('div', { style: { textAlign: 'center', fontSize: '12px', color: 'var(--mint)', padding: '6px' } }, '✅ 今晚已行动，等待天亮…'));
      return;
    }
    const chips = h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center', padding: '8px 0' } });
    const pickTarget = (label, action) => {
      chips.innerHTML = '';
      for (const t of myNight.targets || []) {
        chips.append(h('button', {
          class: 'chip', onclick: async () => {
            try {
              const r = await POST(`/api/rooms/${roomId}/action`, { action, target_seat: t.seat });
              myNight.acted = true;
              if (r.result) toast(r.result, 'care');
              else toast(r.message || '已行动');
              renderNight();
            } catch (e) { toast(e.message, 'warn'); }
          }
        }, `${label} ${t.nickname}`));
      }
    };

    if (myNight.stage === 'wolf') {
      nightSlot.append(h('div', { style: { textAlign: 'center', fontSize: '12.5px', fontWeight: 700, color: '#c2532f' } },
        `🐺 选择今晚的目标${myNight.teammates?.length ? `（队友：${myNight.teammates.join('、')}）` : ''}`));
      pickTarget('🔪', 'kill');
      nightSlot.append(chips);
    } else if (myNight.stage === 'seer') {
      nightSlot.append(h('div', { style: { textAlign: 'center', fontSize: '12.5px', fontWeight: 700, color: 'var(--brand)' } }, '🔮 你想查验谁的身份？'));
      pickTarget('🔍', 'check');
      nightSlot.append(chips);
    } else if (myNight.stage === 'witch') {
      const v = myNight.victim;
      nightSlot.append(h('div', { style: { textAlign: 'center', fontSize: '12.5px', fontWeight: 700, color: 'var(--brand)' } },
        v ? `🧪 今晚 ${v.nickname} 被袭击了` : '🧪 今晚是平安夜'));
      const btnRow = h('div', { style: { display: 'flex', gap: '8px', justifyContent: 'center', padding: '8px 0', flexWrap: 'wrap' } });
      const act = async (action, target) => {
        try {
          const r = await POST(`/api/rooms/${roomId}/action`, { action, target_seat: target });
          myNight.acted = true;
          toast(r.message || '已行动');
          renderNight();
        } catch (e) { toast(e.message, 'warn'); }
      };
      if (myNight.can_save) btnRow.append(h('button', { class: 'btn mini', onclick: () => act('save') }, `💊 救${v ? ` ${v.nickname}` : ''}`));
      if (myNight.can_poison) btnRow.append(h('button', { class: 'btn mini danger', onclick: () => { poisonPicking = !poisonPicking; renderNight(); } }, '☠️ 用毒'));
      btnRow.append(h('button', { class: 'btn mini ghost', onclick: () => act('skip') }, '🌙 不使用'));
      nightSlot.append(btnRow);
      if (poisonPicking && myNight.can_poison) {
        nightSlot.append(h('div', { style: { textAlign: 'center', fontSize: '11px', color: 'var(--ink-3)' } }, '选择毒杀目标：'));
        chips.innerHTML = '';
        for (const t of myNight.targets || []) {
          chips.append(h('button', { class: 'chip', onclick: () => act('poison', t.seat) }, `☠️ ${t.nickname}`));
        }
        nightSlot.append(chips);
      }
    } else if (myNight.title) {
      // 通用夜间动作面板（恐怖等新玩法声明式渲染，无需为每个游戏写专属 UI）
      nightSlot.append(h('div', { style: { textAlign: 'center', fontSize: '12.5px', fontWeight: 700, color: isHorror ? '#c2532f' : 'var(--brand)' } }, myNight.title));
      if (myNight.teammates?.length) nightSlot.append(h('div', { style: { textAlign: 'center', fontSize: '11px', color: '#c2532f', marginTop: '2px' } }, `同伙：${myNight.teammates.join('、')}`));
      if ((myNight.targets || []).length) { pickTarget(myNight.pick_label || '选择', myNight.action); nightSlot.append(chips); }
      if (myNight.can_skip) nightSlot.append(h('button', {
        class: 'btn mini ghost', style: { display: 'block', margin: '8px auto 0' },
        onclick: async () => {
          try { const r = await POST(`/api/rooms/${roomId}/action`, { action: 'skip' }); myNight.acted = true; toast(r.message || '已行动'); renderNight(); }
          catch (e) { toast(e.message, 'warn'); }
        }
      }, '🌙 今夜不行动'));
    }
  }

  function renderActions() {
    actionSlot.innerHTML = '';
    const me = room.players.find((p) => p.user_id === myId);
    if (room.status === 'waiting') {
      const isHost = room.host_id === myId;
      const row = h('div', { style: { display: 'flex', gap: '10px' } });
      if (isHost) {
        row.append(h('button', {
          class: 'btn block', style: { flex: 1 },
          onclick: async () => { try { await POST(`/api/rooms/${roomId}/start`); } catch (e) { toast(e.message, 'warn'); } }
        }, `开始游戏${room.allow_bots ? '（AI 可补位）' : ''}`));
      }
      row.append(h('button', {
        class: `btn block ${me?.ready ? 'ghost' : ''}`, style: { flex: 1 },
        onclick: async () => { try { await POST(`/api/rooms/${roomId}/ready`, { ready: !me?.ready }); } catch (e) { toast(e.message, 'warn'); } }
      }, me?.ready ? '取消准备' : '准备'));
      actionSlot.append(row);
    } else if (room.status === 'ended') {
      actionSlot.append(h('button', { class: 'btn block', onclick: () => nav('/games') }, '回到大厅 · 再来一局'));
    }
    if (room.status !== 'ended') {
      const myTurn = room.phase === 'speak' && room.players.find((p) => p.seat === room.turn_seat)?.user_id === myId;
      const nightMute = room.phase === 'night' && me?.alive;
      const input = h('input', {
        class: 'input', maxlength: myTurn ? 120 : 200,
        placeholder: nightMute ? '🤫 天黑了，不能说话…' : myTurn ? '✋ 轮到你发言了' : '聊两句…',
        disabled: nightMute || undefined,
        style: myTurn ? { borderColor: 'var(--mint)', boxShadow: '0 0 0 4px rgba(98,217,181,.15)' } : {}
      });
      const send = async () => {
        const content = input.value.trim();
        if (!content) return;
        try {
          await POST(`/api/rooms/${roomId}/${myTurn ? 'speak' : 'chat'}`, { content });
          input.value = '';
        } catch (e) { toast(e.message, 'warn'); }
      };
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
      actionSlot.append(h('div', { style: { display: 'flex', gap: '8px', marginTop: '10px' } },
        input,
        h('button', { class: `btn mini ${myTurn ? '' : 'ghost'}`, style: { flexShrink: 0 }, onclick: send, disabled: nightMute || undefined }, myTurn ? '发言' : '发送')
      ));
    }
  }

  function addMsg(m) {
    const mine = m.user_id === myId;
    const bubblePayload = mine ? skinPayload(store.me?.equipped?.bubble) : null;
    const kindCls = m.kind === 'host' ? 'host' : m.kind === 'system' ? 'sys' : m.kind === 'speak' ? 'speak' : '';
    const bubble = h('div', { class: 'm-bubble' }, m.content);
    if (bubblePayload?.bg) {
      bubble.style.background = `linear-gradient(135deg, ${bubblePayload.bg[0]}, ${bubblePayload.bg[1]})`;
      if (bubblePayload.text) bubble.style.color = bubblePayload.text;
    }
    const row = h('div', { class: `chat-msg ${kindCls}` });
    if (m.kind === 'system') {
      row.append(bubble);
    } else {
      row.append(h('div', { class: 'm-body' },
        h('div', { class: 'm-name' },
          m.nickname,
          m.is_ai ? h('span', { class: 'badge-ai' }, '🤖 AI') : null,
          m.kind === 'speak' ? h('span', { style: { color: 'var(--mint)' } }, '· 发言') : null,
          m.kind === 'wolf' ? h('span', { style: { color: '#c2532f' } }, '· 狼队私聊') : null,
          !m.is_ai && !mine && m.kind !== 'system' && m.id
            ? h('span', { style: { cursor: 'pointer', color: 'var(--ink-3)' }, onclick: () => reportSheet('room_message', m.id) }, ' 举报')
            : null
        ),
        bubble));
    }
    chatBox.append(row);
    chatWrap.scrollTop = chatWrap.scrollHeight;
  }

  function renderAll() { renderSeats(); renderInfo(); renderNight(); renderActions(); }
  for (const m of data.messages || []) addMsg(m);
  renderAll();

  function menuSheet() {
    sheet((box, close) => {
      box.append(h('h3', {}, '房间操作'));
      if (room.host_id === myId && room.status === 'waiting') {
        for (const p of room.players.filter((x) => x.user_id !== myId && !x.is_bot)) {
          box.append(h('button', {
            class: 'menu-item glass', style: { width: '100%', marginBottom: '8px' },
            onclick: async () => { close(); try { await POST(`/api/rooms/${roomId}/kick`, { seat: p.seat }); } catch (e) { toast(e.message, 'warn'); } }
          }, `🚪 请 ${p.nickname} 离开`));
        }
      }
      box.append(h('button', {
        class: 'menu-item glass', style: { width: '100%', marginBottom: '8px', color: 'var(--danger)' },
        onclick: () => { close(); leave(true); }
      }, '👋 退出房间'));
      box.append(h('button', { class: 'btn block ghost', onclick: close }, '取消'));
    });
  }

  function leave(confirm) {
    const doLeave = async () => {
      try { await POST(`/api/rooms/${roomId}/leave`); } catch { /* 已退出 */ }
      nav('/games');
    };
    if (confirm && room.status === 'playing') {
      confirmSheet('退出房间', '游戏进行中退出将视为出局，确定吗？', '确定退出', doLeave);
    } else doLeave();
  }

  // ---- SSE 实时 ----
  const es = sse(`/api/rooms/${roomId}/events`, {
    state: (s) => {
      const wasWaiting = room.status === 'waiting';
      const prevPhase = room.phase;
      room = { ...room, ...s };
      if (wasWaiting && s.status === 'playing') toast(isHorror ? '游戏开始！天黑请闭眼，活到黎明 🕯' : isWolfGame ? '游戏开始！天黑请闭眼 🌙' : '游戏开始！查看你的词 👀');
      if (prevPhase === 'night' && s.phase !== 'night') { myNight = null; poisonPicking = false; }
      renderAll();
    },
    word: (w) => { myWord = w.word; renderInfo(); toast(`你的词：「${w.word}」`, 'care'); },
    role: (r) => {
      myRole = r;
      seerLog = r.seer_log || seerLog;
      renderInfo();
      toast(`你的身份：${r.icon} ${r.name}`, 'care');
    },
    night: (n) => { myNight = n; poisonPicking = false; renderNight(); },
    seer_result: (r) => {
      seerLog[room.round] = `${r.nickname}：${r.result}`;
      renderInfo();
      toast(`🔮 查验结果：${r.nickname} 是 ${r.result}`, 'care');
    },
    wolf_chat: (m) => addMsg({ user_id: 0, nickname: '🐺 狼队频道', kind: 'wolf', content: m.text, is_ai: false }),
    accomplice_chat: (m) => addMsg({ user_id: 0, nickname: '🔪 同伙频道', kind: 'wolf', content: m.text, is_ai: false }),
    sense_result: (r) => {
      if (myRole) { myRole.clue_log = myRole.clue_log || {}; myRole.clue_log[r.round || room.round] = `${r.nickname}：${r.result}`; }
      renderInfo();
    },
    msg: (m) => addMsg(m),
    kicked: () => { toast('你被房主请离了房间'); nav('/games'); },
    closed: (c) => { toast(c.reason || '房间已关闭'); nav('/games'); }
  });

  return () => {
    es.close();
    clearInterval(timerInt);
    page.style.background = '';
    page.style.color = '';
  };
}
