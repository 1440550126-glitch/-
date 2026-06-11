// 游戏房间：座位 / 准备 / AI 主持 / 发言 / 投票 / 结算（SSE 驱动）
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
  const myId = store.me?.id;

  // 房主装备的房间主题皮肤（纯外观换肤）
  const theme = room.theme ? skinPayload(room.theme) : null;
  if (theme?.bg) {
    page.style.background = `linear-gradient(165deg, ${theme.bg[0]}, ${theme.bg[1]})`;
    page.style.borderRadius = '0';
    page.classList.add('room-themed');
    page.style.color = '#f3eefc';
  }

  const titleEl = h('h1', { style: { fontSize: '17px' } }, room.name);
  const phaseEl = h('div', { class: 'sub', style: theme ? { color: 'rgba(255,255,255,.6)' } : {} }, '');
  const seatsEl = h('div', { class: 'seats' });
  const wordSlot = h('div', {});
  const chatBox = h('div', { class: 'chat-box' });
  const actionSlot = h('div', { style: { marginTop: '10px' } });
  const timerEl = h('span', { style: { fontSize: '11px', color: 'var(--brand)', fontWeight: 700 } });

  const chatWrap = h('div', { class: 'glass card', style: { maxHeight: '38vh', overflowY: 'auto', background: theme ? 'rgba(255,255,255,.92)' : undefined } }, chatBox);

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
        theme?.emoji ? h('span', { style: { fontSize: '16px' } }, theme.emoji) : '🕵️',
        `谁是卧底 · 房间号 ${room.id}`,
        h('span', { class: 'badge-ai' }, '🤖 AI 主持')),
      seatsEl,
      wordSlot
    ),
    chatWrap,
    actionSlot
  );

  // ---- 渲染函数 ----
  let timerInt = setInterval(() => {
    if (room.phase_ends_at) {
      const left = Math.max(0, Math.ceil((room.phase_ends_at - Date.now()) / 1000));
      timerEl.textContent = left > 0 ? `⏱ ${left}s` : '';
    } else timerEl.textContent = '';
  }, 500);

  function phaseName() {
    if (room.status === 'waiting') return '等待开始';
    if (room.status === 'ended') return '已结束';
    return { describe: `第 ${room.round} 轮 · 描述`, vote: `第 ${room.round} 轮 · 投票`, ended: '已结束' }[room.phase] || '';
  }

  function renderSeats() {
    seatsEl.innerHTML = '';
    phaseEl.textContent = phaseName();
    const me = room.players.find((p) => p.user_id === myId);
    const iVoted = me?.voted;
    for (const p of room.players) {
      const isTurn = room.phase === 'describe' && room.turn_seat === p.seat;
      const canVote = room.status === 'playing' && room.phase === 'vote' && me?.alive && !iVoted && p.alive && p.user_id !== myId;
      const seat = h('div', { class: `seat filled ${isTurn ? 'turn' : ''} ${p.alive === false ? 'dead' : ''}` },
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
      );
      seatsEl.append(seat);
    }
    for (let i = room.players.length; i < room.max_players; i++) {
      seatsEl.append(h('div', { class: 'seat' }, h('span', { style: { fontSize: '18px', opacity: 0.3 } }, '＋'), h('div', { class: 's-name' }, '虚位以待')));
    }
  }

  function renderWord() {
    wordSlot.innerHTML = '';
    if (room.status === 'playing' && myWord) {
      wordSlot.append(h('div', { class: 'word-card' },
        h('div', { style: { fontSize: '10.5px', color: 'var(--ink-3)', marginBottom: '4px' } }, '你的词（只有你能看到）'),
        h('div', { class: 'w-word' }, myWord),
        h('div', { style: { fontSize: '10.5px', color: 'var(--ink-3)', marginTop: '4px' } }, '描述它，但别说出它！')
      ));
    }
    if (room.status === 'ended' && room.reveal) {
      wordSlot.append(h('div', { class: 'word-card' },
        h('div', { style: { fontWeight: 800, fontSize: '17px', marginBottom: '8px' } },
          room.winner === 'civilian' ? '🎉 平民阵营胜利！' : '🕶️ 卧底阵营胜利！'),
        h('div', { style: { fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.9 } },
          room.reveal.map((r) => `${r.role === 'undercover' ? '🕶' : '🙂'} ${r.nickname}「${r.word}」`).join('　'))
      ));
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
    // 输入区：描述阶段轮到我 → 发言；其他 → 聊天
    if (room.status !== 'ended') {
      const myTurn = room.phase === 'describe' && room.players.find((p) => p.seat === room.turn_seat)?.user_id === myId;
      const input = h('input', {
        class: 'input', maxlength: myTurn ? 100 : 200,
        placeholder: myTurn ? '✋ 轮到你描述了（不能说出你的词）' : '聊两句…',
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
        h('button', { class: `btn mini ${myTurn ? '' : 'ghost'}`, style: { flexShrink: 0 }, onclick: send }, myTurn ? '发言' : '发送')
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
          !m.is_ai && !mine && m.kind !== 'system'
            ? h('span', { style: { cursor: 'pointer', color: 'var(--ink-3)' }, onclick: () => reportSheet('room_message', m.id) }, ' 举报')
            : null
        ),
        bubble));
    }
    chatBox.append(row);
    chatWrap.scrollTop = chatWrap.scrollHeight;
  }

  function renderAll() { renderSeats(); renderWord(); renderActions(); }
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
      room = { ...room, ...s };
      if (wasWaiting && s.status === 'playing') toast('游戏开始！查看你的词 👀');
      renderAll();
    },
    word: (w) => { myWord = w.word; renderWord(); toast(`你的词：「${w.word}」`, 'care'); },
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
