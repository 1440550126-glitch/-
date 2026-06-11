// 桌游大厅：房间列表（SSE 实时）+ 创建房间 + AI 暖场组局提醒
import { GET, POST, sse } from '../api.js';
import { h, toast, sheet, emptyState, aiBadge } from '../ui.js';
import { nav } from '../router.js';

export async function renderGames(page) {
  const list = h('div', {});
  const noticeSlot = h('div', {});

  page.append(
    h('div', { class: 'topbar' },
      h('div', {}, h('h1', {}, '桌游大厅'), h('div', { class: 'sub' }, '玩法全免费 · 不卖胜负')),
      h('div', { class: 'spacer' }),
      h('button', { class: 'btn mini', onclick: createSheet }, '+ 开房间')
    ),
    h('div', { class: 'glass card', style: { display: 'flex', gap: '12px', alignItems: 'center' } },
      h('div', { style: { fontSize: '34px' } }, '🕵️'),
      h('div', { style: { flex: 1 } },
        h('div', { style: { fontWeight: 700 } }, '谁是卧底'),
        h('div', { style: { fontSize: '11.5px', color: 'var(--ink-2)', marginTop: '2px' } },
          '4-8 人 · AI 主持 · 一个人也能玩（AI 陪练补位）')),
      h('button', { class: 'btn mini ghost', onclick: createSheet }, '开局')
    ),
    h('div', { style: { display: 'flex', gap: '10px', marginBottom: '14px' } },
      ['🐺 狼人杀', '📖 剧本杀', '🗝 密室逃脱'].map((name) =>
        h('div', { class: 'glass', style: { flex: 1, textAlign: 'center', padding: '13px 4px', fontSize: '12px', color: 'var(--ink-3)' } },
          h('div', { style: { fontSize: '20px', marginBottom: '3px', filter: 'grayscale(.6)', opacity: 0.7 } }, name.split(' ')[0]),
          name.split(' ')[1], h('div', { style: { fontSize: '9px', marginTop: '2px' } }, '即将上线')))
    ),
    noticeSlot,
    h('div', { style: { fontWeight: 700, fontSize: '14px', margin: '4px 2px 10px' } }, '正在等人的房间'),
    list
  );

  function renderRooms(items, myRoomId) {
    list.innerHTML = '';
    if (myRoomId) {
      list.append(h('div', { class: 'glass topic-banner', onclick: () => nav(`/room/${myRoomId}`) },
        h('div', { class: 'tb-title' }, '🎲 你有一个进行中的房间'),
        h('div', { class: 'tb-desc' }, `房间号 ${myRoomId}，点击回到房间`),
        h('button', { class: 'btn mini tb-go' }, '回去')
      ));
    }
    if (!items.length) {
      list.append(emptyState('现在没有等待中的房间', '开一个吧，AI 陪练随时可以补位'));
      return;
    }
    for (const r of items) {
      list.append(h('div', {
        class: 'glass room-item', style: { cursor: 'pointer' },
        onclick: async () => {
          try { await POST(`/api/rooms/${r.id}/join`); nav(`/room/${r.id}`); }
          catch (e) {
            if (e.extra?.room_id) nav(`/room/${e.extra.room_id}`);
            else toast(e.message, 'warn');
          }
        }
      },
        h('div', { class: 'ri-emoji' }, r.status === 'playing' ? '🎮' : '🕵️'),
        h('div', { style: { flex: 1 } },
          h('div', { class: 'ri-name' }, r.name),
          h('div', { class: 'ri-meta' }, `房间号 ${r.id} · ${r.players}/${r.max_players} 人 · ${r.status === 'playing' ? '游戏中' : '等待中'}${r.allow_bots ? ' · AI 可补位' : ''}`)),
        h('button', { class: 'btn mini ghost' }, r.status === 'playing' ? '围观' : '加入')
      ));
    }
  }

  function createSheet() {
    sheet((box, close) => {
      const name = h('input', { class: 'input', placeholder: '给房间起个名字（可选）', maxlength: 20 });
      let maxP = 6, bots = true;
      const seatRow = h('div', { style: { display: 'flex', gap: '8px', marginTop: '4px' } });
      const renderSeats = () => {
        seatRow.innerHTML = '';
        for (const n of [4, 5, 6, 7, 8]) {
          seatRow.append(h('button', { class: `chip ${maxP === n ? 'active' : ''}`, onclick: () => { maxP = n; renderSeats(); } }, `${n}人`));
        }
      };
      renderSeats();
      const botSwitch = h('button', { class: `switch ${bots ? 'on' : ''}`, onclick: () => { bots = !bots; botSwitch.classList.toggle('on', bots); } });
      box.append(
        h('h3', {}, '开一局谁是卧底'),
        h('div', { class: 'field' }, h('label', {}, '房间名'), name),
        h('div', { class: 'field' }, h('label', {}, '人数上限'), seatRow),
        h('div', { class: 'menu-item', style: { padding: '10px 0' } },
          h('div', { style: { flex: 1 } },
            h('div', { style: { fontSize: '14px' } }, 'AI 陪练补位'),
            h('div', { style: { fontSize: '11px', color: 'var(--ink-3)' } }, '人不够时由带 AI 标识的小句灵补位')),
          botSwitch),
        h('button', {
          class: 'btn block', style: { marginTop: '8px' },
          onclick: async () => {
            try {
              const { room } = await POST('/api/rooms', { name: name.value.trim(), max_players: maxP, allow_bots: bots });
              close();
              nav(`/room/${room.id}`);
            } catch (e) {
              if (e.extra?.room_id) { close(); nav(`/room/${e.extra.room_id}`); }
              else toast(e.message, 'warn');
            }
          }
        }, '创建房间')
      );
    });
  }

  // 初始加载 + SSE 实时
  try {
    const { items, my_room_id } = await GET('/api/rooms');
    renderRooms(items, my_room_id);
  } catch (e) { toast(e.message, 'warn'); }

  const es = sse('/api/lobby/events', {
    rooms: (items) => renderRooms(items, null),
    notice: (n) => {
      noticeSlot.innerHTML = '';
      noticeSlot.append(h('div', { class: 'glass topic-banner' },
        h('div', { class: 'tb-title' }, '💬 ', n.from, ' ', aiBadge(n.ai_label)),
        h('div', { class: 'tb-desc' }, n.content)
      ));
    }
  });
  return () => es.close();
}
