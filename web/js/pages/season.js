// 凶夜赛季通行证：玩多人对局攒印记升级，领取纯外观奖励；高级档一次性解锁全套
import { GET, POST } from '../api.js';
import { h, toast, rarityName, fen, confirmSheet } from '../ui.js';
import { refreshMe } from '../store.js';
import { nav } from '../router.js';

const RARITY_CLS = { normal: 'r-normal', rare: 'r-rare', fine: 'r-fine', epic: 'r-epic', legend: 'r-legend', limited: 'r-limited' };
const TYPE_ICON = { card_frame: '🖼', avatar_frame: '⭕', bubble: '💬', anim_fx: '✨', room_theme: '🏠', unknown: '🎁' };

export async function renderSeason(page) {
  let data;
  try { data = await GET('/api/season'); }
  catch (e) { toast(e.message, 'warn'); nav('/games'); return; }

  const root = h('div', {});
  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', {}, h('h1', { style: { fontSize: '18px' } }, '凶夜赛季通行证'), h('div', { class: 'sub' }, '玩对局攒印记 · 奖励纯外观不卖胜负')),
      h('div', { class: 'spacer' })
    ),
    root
  );

  function rewardCell(skin, claimable, claimed, locked, onClaim, lockText) {
    if (!skin) return h('div', { class: 'sp-cell empty' }, '—');
    const cell = h('div', { class: `sp-cell ${claimed ? 'claimed' : claimable ? 'ready' : 'locked'}` },
      h('div', { class: 'sp-ic' }, TYPE_ICON[skin.type] || '🎁'),
      h('div', { class: 'sp-info' },
        h('div', { class: 'sp-name' }, skin.name),
        h('span', { class: `badge-rarity ${RARITY_CLS[skin.rarity] || 'r-normal'}` }, rarityName[skin.rarity] || '普通'))
    );
    if (claimed) cell.append(h('div', { class: 'sp-tag done' }, '已领取 ✓'));
    else if (claimable) { const b = h('button', { class: 'btn mini sp-claim', onclick: onClaim }, '领取'); cell.append(b); }
    else cell.append(h('div', { class: 'sp-tag' }, lockText || '未解锁'));
    return cell;
  }

  function render() {
    root.innerHTML = '';
    const { season, progress, track } = data;
    const inLevel = progress.level >= season.max_level ? season.points_per_level : (progress.points - progress.level * season.points_per_level);
    const pct = Math.max(0, Math.min(100, Math.round((inLevel / season.points_per_level) * 100)));

    // 头部：进度
    root.append(h('div', { class: 'glass card sp-hero' },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: '10px' } },
        h('div', { class: 'sp-lv' }, 'Lv ', String(progress.level)),
        h('div', { style: { flex: 1 } },
          h('div', { style: { fontWeight: 800, fontSize: '15px' } }, season.name),
          h('div', { style: { fontSize: '11px', color: 'var(--ink-2)', marginTop: '2px' } },
            progress.premium ? '🌙 已解锁高级通行证' : '免费档进行中 · 解锁高级档领全套'))
      ),
      h('div', { class: 'sp-bar' }, h('div', { class: 'sp-bar-fill', style: { width: pct + '%' } })),
      h('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--ink-3)', marginTop: '5px' } },
        h('span', {}, `🔮 ${progress.points} 印记`),
        h('span', {}, progress.next_level_at ? `距 Lv${progress.level + 1} 还差 ${progress.next_level_at - progress.points}` : '已满级 🎉')),
      h('div', { style: { fontSize: '11px', color: 'var(--ink-3)', marginTop: '6px', lineHeight: 1.6 } },
        `每局多人对局 +${progress.per_game} 印记，当日首局额外 +${progress.first_game_bonus}（每日上限 ${progress.daily_cap}，今日已得 ${progress.today_points}）`)
    ));

    if (!progress.premium) {
      root.append(h('button', { class: 'btn gold block', style: { marginBottom: '14px' }, onclick: unlockPremium },
        `🌙 解锁高级通行证 · ¥${fen(season.premium_price_fen)}`));
    }

    // 轨道表头
    root.append(h('div', { class: 'sp-track-head' },
      h('div', { style: { width: '38px' } }, '等级'),
      h('div', { style: { flex: 1, textAlign: 'center' } }, '免费档'),
      h('div', { style: { flex: 1, textAlign: 'center' } }, '🌙 高级档')));

    for (const t of track) {
      root.append(h('div', { class: `sp-row ${t.reached ? 'reached' : ''}` },
        h('div', { class: 'sp-lv-cell' }, h('div', { class: 'sp-lv-num' }, String(t.level)), h('div', { class: 'sp-lv-pt' }, t.points_at)),
        rewardCell(t.free, t.reached && !t.free_claimed, t.free_claimed, !t.reached, () => claim(t.level, 'free'), '未达等级'),
        rewardCell(t.premium, t.reached && data.progress.premium && !t.premium_claimed, t.premium_claimed,
          !(t.reached && data.progress.premium), () => claim(t.level, 'premium'),
          !t.reached ? '未达等级' : '需高级档')
      ));
    }

    root.append(h('div', { class: 'notice-bar', style: { marginTop: '14px' } },
      '赛季奖励均为外观（卡框/头像框/气泡/房间主题），不影响任何对局公平。领取后可在「商城 → 我的皮肤」装备。'));
  }

  async function claim(level, track) {
    try {
      const r = await POST('/api/season/claim', { level, track });
      toast(`已领取「${r.skin?.name || '奖励'}」🎉 去商城装备吧`);
      data = await GET('/api/season');
      render();
    } catch (e) {
      if (e.extra?.need_premium) unlockPremium();
      else toast(e.message, 'warn');
    }
  }

  function unlockPremium() {
    confirmSheet('解锁高级通行证', `${data.season.name} 高级档：一次性解锁全部 ${data.track.filter((t) => t.premium).length} 档高级外观奖励（含终极「迷雾庄园」房间主题）。¥${fen(data.season.premium_price_fen)}（沙盒支付）。`,
      `确认支付 ¥${fen(data.season.premium_price_fen)}`, async () => {
        try {
          const { order } = await POST('/api/shop/orders', { kind: 'season', item_id: data.season.id });
          await POST(`/api/shop/orders/${order.id}/pay`);
          await refreshMe();
          toast('已解锁高级通行证 🌙 已达等级的高级奖励现在可以领取');
          data = await GET('/api/season');
          render();
        } catch (e) { toast(e.message, 'warn'); }
      }, false);
  }

  render();
}
