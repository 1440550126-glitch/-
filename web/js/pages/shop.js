// 皮肤商城：纯外观，不卖任何对局优势
import { GET, POST } from '../api.js';
import { h, toast, sheet, rarityName, fen } from '../ui.js';
import { store, refreshMe } from '../store.js';
import { nav } from '../router.js';

const TYPE_NAMES = { card_frame: '卡片边框', avatar_frame: '头像框', bubble: '聊天气泡', anim_fx: '动画特效', room_theme: '房间主题' };

function swatchEl(skin) {
  const p = skin.payload || {};
  const bg = p.gradient || p.ring || p.bg || ['#eee', '#ddd'];
  const emoji = { card_frame: '🖼', avatar_frame: '😺', bubble: '💬', anim_fx: '✨', room_theme: p.emoji || '🏠' }[skin.type];
  return h('div', { class: 'skin-swatch', style: { background: `linear-gradient(135deg, ${bg[0]}, ${bg[1]})` } },
    h('span', { style: { filter: 'drop-shadow(0 3px 6px rgba(0,0,0,.18))' } }, emoji));
}

export async function renderShop(page) {
  let cat;
  try { cat = await GET('/api/shop/catalog'); }
  catch (e) { toast(e.message, 'warn'); return; }

  let type = 'card_frame';
  const grid = h('div', { class: 'shop-grid' });
  const chipRow = h('div', { class: 'chip-row' });

  const equipped = () => store.me?.equipped || {};

  function renderChips() {
    chipRow.innerHTML = '';
    for (const [id, name] of Object.entries(TYPE_NAMES)) {
      chipRow.append(h('button', { class: `chip ${type === id ? 'active' : ''}`, onclick: () => { type = id; renderChips(); renderGrid(); } }, name));
    }
  }

  function renderGrid() {
    grid.innerHTML = '';
    const items = cat.skins.filter((s) => s.type === type);
    for (const skin of items) {
      const isEquipped = equipped()[skin.type] === skin.id;
      const owned = skin.owned;
      const btn = h('button', {
        class: `btn mini ${owned ? (isEquipped ? 'ghost' : '') : 'gold'}`,
        onclick: () => owned ? toggleEquip(skin, isEquipped) : buySheet(skin)
      }, owned ? (isEquipped ? '卸下' : '装备') : `¥${fen(skin.price_fen)}`);
      grid.append(h('div', { class: 'glass skin-card' },
        swatchEl(skin),
        h('div', { class: 'sk-name' }, skin.name, h('span', { class: `badge-rarity r-${skin.rarity}` }, rarityName[skin.rarity] || skin.rarity)),
        h('div', { class: 'sk-blurb' }, skin.blurb),
        h('div', { class: 'sk-foot' },
          h('span', { class: 'sk-price' }, skin.price_fen === 0 ? '免费' : owned ? '已拥有' : `¥${fen(skin.price_fen)}`),
          btn)
      ));
    }
  }

  async function toggleEquip(skin, isEquipped) {
    try {
      const r = await POST('/api/me/equip', { type: skin.type, skin_id: isEquipped ? null : skin.id });
      store.me.equipped = r.equipped;
      toast(isEquipped ? '已卸下' : `已装备「${skin.name}」`);
      renderGrid();
    } catch (e) { toast(e.message, 'warn'); }
  }

  function buySheet(skin) {
    sheet((box, close) => {
      box.append(
        h('h3', {}, `购买「${skin.name}」`),
        swatchEl(skin),
        h('p', { style: { fontSize: '12.5px', color: 'var(--ink-2)', margin: '12px 0', lineHeight: 1.7 } },
          `${skin.blurb}。${TYPE_NAMES[skin.type]} · ${rarityName[skin.rarity]}。`,
          h('br'), '皮肤仅改变外观，不影响任何玩法与公平性。'),
        h('button', {
          class: 'btn block gold',
          onclick: async () => {
            try {
              const { order, pay_hint } = await POST('/api/shop/orders', { kind: 'skin', item_id: skin.id });
              const r = await POST(`/api/shop/orders/${order.id}/pay`);
              store.me = r.me;
              skin.owned = true;
              toast(`购买成功！${pay_hint ? '' : ''}已放入你的衣橱 🎀`);
              close(); renderGrid();
            } catch (e) { toast(e.message, 'warn'); }
          }
        }, `沙盒支付 ¥${fen(skin.price_fen)}`),
        h('div', { class: 'notice-bar', style: { marginTop: '12px' } }, '当前为沙盒支付演示。正式版将接入微信支付/支付宝，iOS 走 Apple 内购。')
      );
    });
  }

  page.append(
    h('div', { class: 'topbar' },
      h('div', {}, h('h1', {}, '皮肤商城'), h('div', { class: 'sub' }, '只换好看，不卖胜负')),
      h('div', { class: 'spacer' }),
      h('button', { class: 'icon-btn', onclick: () => nav('/member') }, '👑')
    ),
    h('div', { class: 'glass topic-banner', onclick: () => nav('/member') },
      h('div', { class: 'tb-title' }, '👑 句灵会员 9.9 元/月'),
      h('div', { class: 'tb-desc' }, '解锁文字变动画全部基础风格 + 高级额度 8 折'),
      h('button', { class: 'btn mini tb-go gold' }, '开通')
    ),
    chipRow, grid,
    h('div', { class: 'notice-bar', style: { marginTop: '14px' } }, cat.fair_play)
  );
  renderChips();
  renderGrid();
  await refreshMe();
  renderGrid();
}
