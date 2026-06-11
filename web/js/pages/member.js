// 会员中心：9.9 元/月 + 星尘额度（高级 AI）
import { GET, POST } from '../api.js';
import { h, toast, mascot, fen } from '../ui.js';
import { store, refreshMe } from '../store.js';

export async function renderMember(page) {
  let cat;
  try { cat = await GET('/api/shop/catalog'); }
  catch (e) { toast(e.message, 'warn'); return; }
  await refreshMe();
  const me = store.me;

  let planId = 'm3';
  const planRow = h('div', { style: { display: 'flex', gap: '10px', margin: '14px 0' } });
  function renderPlans() {
    planRow.innerHTML = '';
    for (const p of cat.member_plans) {
      planRow.append(h('button', {
        class: `plan ${planId === p.id ? 'sel' : ''}`,
        onclick: () => { planId = p.id; renderPlans(); }
      },
        p.tag ? h('div', { class: 'p-tag' }, p.tag) : null,
        h('div', { style: { fontSize: '12px', fontWeight: 600 } }, p.name.replace('句灵会员 · ', '')),
        h('div', { class: 'p-price' }, h('small', {}, '¥'), fen(p.price_fen)),
        h('div', { style: { fontSize: '9.5px', color: 'var(--ink-3)', marginTop: '3px' } }, p.blurb)
      ));
    }
  }
  renderPlans();

  async function buy(kind, itemId) {
    try {
      const { order } = await POST('/api/shop/orders', { kind, item_id: itemId });
      const r = await POST(`/api/shop/orders/${order.id}/pay`);
      store.me = r.me;
      toast(kind === 'member' ? '会员开通成功！文字现在归你点亮 ✨' : '额度到账！去试试高级动画风格吧 ✦');
      page.innerHTML = '';
      renderMember(page);
    } catch (e) { toast(e.message, 'warn'); }
  }

  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', {}, h('h1', { style: { fontSize: '18px' } }, '会员中心')),
      h('div', { class: 'spacer' })
    ),
    h('div', { class: 'member-hero' },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: '14px' } },
        mascot(72),
        h('div', {},
          h('h2', {}, me?.is_member ? '你已是句灵会员 👑' : '句灵会员'),
          h('div', { style: { fontSize: '12px', color: 'var(--ink-2)', marginTop: '4px' } },
            me?.is_member
              ? `有效期至 ${new Date(me.member_until).toLocaleDateString()}`
              : '一杯奶茶钱，让你的文字活一个月')
        ))
    ),
    h('div', { class: 'glass card' },
      h('div', { style: { fontWeight: 700, marginBottom: '6px' } }, '会员权益'),
      (cat.member_benefits || []).map((b) => h('div', { class: 'benefit' }, '🌸 ', b))
    ),
    planRow,
    h('button', { class: 'btn gold block', onclick: () => buy('member', planId) },
      me?.is_member ? '续费会员（沙盒支付）' : '立即开通（沙盒支付）'),
    h('div', { class: 'glass card', style: { marginTop: '18px' } },
      h('div', { style: { fontWeight: 700, marginBottom: '4px' } }, `✦ 星尘额度（高级 AI） · 余额 ${me?.credits ?? 0} 点`),
      h('div', { style: { fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.7, marginBottom: '12px' } },
        '高级动画风格由更强的大模型担任导演，按次消耗额度（会员 8 折）。生成前会展示预计消耗。'),
      h('div', { style: { display: 'flex', gap: '10px' } },
        (cat.credit_packs || []).map((p) => h('button', {
          class: 'plan', style: { position: 'relative' },
          onclick: () => buy('credits', p.id)
        },
          p.tag ? h('div', { class: 'p-tag' }, p.tag) : null,
          h('div', { style: { fontSize: '13px', fontWeight: 700 } }, `✦ ${p.credits} 点`),
          h('div', { class: 'p-price' }, h('small', {}, '¥'), fen(p.price_fen)),
          h('div', { style: { fontSize: '9.5px', color: 'var(--ink-3)', marginTop: '3px' } }, p.blurb)
        )))
    ),
    h('div', { class: 'notice-bar', style: { marginTop: '14px' } },
      '会员不包含高级模型调用；高级风格按次消耗星尘额度。沙盒支付仅供演示，正式版接入微信/支付宝/Apple 内购。',
      h('br'), '青少年模式下无法购买。理性消费，量力而行。')
  );
}
