// 桌游大厅：多玩法（谁是卧底/狼人杀）+ 房间列表（SSE 实时）+ AI 暖场组局提醒
import { GET, POST, sse } from '../api.js';
import { h, toast, sheet, emptyState, aiBadge } from '../ui.js';
import { nav } from '../router.js';

const GAME_DESC = {
  undercover: '4-8 人 · 文字推理 · 十分钟一局',
  werewolf: '6-12 人 · 狼人/预言家/女巫 · 烧脑对抗',
  horror: '5-10 人 · 凶手藏在我们中间 · 随机灵异事件 · 越夜越上头'
};

export async function renderGames(page) {
  const list = h('div', {});
  const noticeSlot = h('div', {});
  let games = [];

  page.append(
    h('div', { class: 'topbar' },
      h('div', {}, h('h1', {}, '桌游大厅'), h('div', { class: 'sub' }, '玩法全免费 · 不卖胜负 · AI 主持')),
      h('div', { class: 'spacer' }),
      h('button', { class: 'btn mini', onclick: () => createSheet() }, '+ 开房间')
    )
  );

  const featured = h('div', {});
  page.append(featured, h('div', { style: { display: 'flex', gap: '10px', marginBottom: '14px' } },
    ['📖 剧本杀', '🗝 密室逃脱', '🐢 海龟汤'].map((name) =>
      h('div', { class: 'glass', style: { flex: 1, textAlign: 'center', padding: '13px 4px', fontSize: '12px', color: 'var(--ink-3)' } },
        h('div', { style: { fontSize: '20px', marginBottom: '3px', filter: 'grayscale(.6)', opacity: 0.7 } }, name.split(' ')[0]),
        name.split(' ')[1], h('div', { style: { fontSize: '9px', marginTop: '2px' } }, '即将上线')))
  ),
  noticeSlot,
  h('div', { style: { fontWeight: 700, fontSize: '14px', margin: '4px 2px 10px' } }, '正在等人的房间'),
  list);

  function renderFeatured() {
    featured.innerHTML = '';
    for (const g of games) {
      featured.append(h('div', { class: 'glass card', style: { display: 'flex', gap: '12px', alignItems: 'center' } },
        h('div', { style: { fontSize: '34px' } }, g.icon),
        h('div', { style: { flex: 1 } },
          h('div', { style: { fontWeight: 700 } }, g.name),
          h('div', { style: { fontSize: '11.5px', color: 'var(--ink-2)', marginTop: '2px' } },
            `${GAME_DESC[g.type] || ''} · AI 陪练可补位`)),
        h('button', { class: 'btn mini ghost', onclick: () => createSheet(g.type) }, '开局')
      ));
    }
  }

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
        h('div', { class: 'ri-emoji' }, r.status === 'playing' ? '🎮' : (r.icon || '🎲')),
        h('div', { style: { flex: 1 } },
          h('div', { class: 'ri-name' }, r.name, h('span', { class: 'chip', style: { marginLeft: '6px', padding: '2px 8px', fontSize: '10px' } }, r.game_name || '')),
          h('div', { class: 'ri-meta' }, `房间号 ${r.id} · ${r.players}/${r.max_players} 人 · ${r.status === 'playing' ? '游戏中' : '等待中'}${r.allow_bots ? ' · AI 可补位' : ''}`)),
        h('button', { class: 'btn mini ghost' }, r.status === 'playing' ? '围观' : '加入')
      ));
    }
  }

  function createSheet(presetType) {
    sheet((box, close) => {
      const name = h('input', { class: 'input', placeholder: '给房间起个名字（可选）', maxlength: 20 });
      let gameType = presetType || games[0]?.type || 'undercover';
      let maxP = 0, bots = true;
      const gameRow = h('div', { style: { display: 'flex', gap: '8px' } });
      const seatRow = h('div', { style: { display: 'flex', gap: '8px', marginTop: '4px', flexWrap: 'wrap' } });

      const renderGameChips = () => {
        gameRow.innerHTML = '';
        for (const g of games) {
          gameRow.append(h('button', {
            class: `chip ${gameType === g.type ? 'active' : ''}`,
            onclick: () => { gameType = g.type; maxP = 0; renderGameChips(); renderSeats(); }
          }, `${g.icon} ${g.name}`));
        }
      };
      const renderSeats = () => {
        const g = games.find((x) => x.type === gameType) || { min: 4, max: 8 };
        if (!maxP) maxP = Math.min(g.max, Math.max(g.min, gameType === 'werewolf' ? 8 : 6));
        seatRow.innerHTML = '';
        for (let n = g.min; n <= g.max; n++) {
          seatRow.append(h('button', { class: `chip ${maxP === n ? 'active' : ''}`, onclick: () => { maxP = n; renderSeats(); } }, `${n}人`));
        }
      };
      renderGameChips(); renderSeats();

      const botSwitch = h('button', { class: `switch ${bots ? 'on' : ''}`, onclick: () => { bots = !bots; botSwitch.classList.toggle('on', bots); } });
      box.append(
        h('h3', {}, '开一局'),
        h('div', { class: 'field' }, h('label', {}, '玩法'), gameRow),
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
              const { room } = await POST('/api/rooms', { name: name.value.trim(), game_type: gameType, max_players: maxP, allow_bots: bots });
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

  try {
    const data = await GET('/api/rooms');
    games = data.games || [];
    renderFeatured();
    renderRooms(data.items, data.my_room_id);
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
