// 设置与隐私：AI 暖场开关 / 青少年模式 / 拉黑管理 / 注销 / 协议文档
import { GET, PATCH, DEL, setToken } from '../api.js';
import { h, toast, confirmSheet, emptyState, avatarEl } from '../ui.js';
import { store, refreshMe, logout } from '../store.js';
import { nav } from '../router.js';

function switchRow(label, desc, key, onFlip) {
  const on = !!store.me?.settings?.[key];
  const sw = h('button', { class: `switch ${on ? 'on' : ''}` });
  sw.addEventListener('click', async () => {
    const next = !sw.classList.contains('on');
    try {
      const me = await PATCH('/api/me', { settings: { [key]: next } });
      store.me = me;
      sw.classList.toggle('on', next);
      onFlip?.(next);
    } catch (e) { toast(e.message, 'warn'); }
  });
  return h('div', { class: 'menu-item' },
    h('div', { style: { flex: 1 } },
      h('div', {}, label),
      h('div', { style: { fontSize: '11px', color: 'var(--ink-3)', marginTop: '2px', fontWeight: 400 } }, desc)),
    sw);
}

export async function renderSettings(page) {
  await refreshMe();
  if (!store.me) { nav('/login'); return; }

  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', {}, h('h1', { style: { fontSize: '18px' } }, '设置与隐私')),
      h('div', { class: 'spacer' })
    ),
    h('div', { class: 'glass menu-list', style: { marginBottom: '14px' } },
      switchRow('隐藏 AI 暖场内容', '信息流不再展示 AI 暖场官的动态', 'hide_ai_posts'),
      switchRow('关闭 AI 暖场互动', '小句灵将不再评论你的文案', 'no_ai_warmup'),
      switchRow('青少年模式', '关闭全部消费功能，过滤部分内容', 'teen_mode',
        (on) => toast(on ? '青少年模式已开启，消费功能已关闭 💚' : '青少年模式已关闭')),
      switchRow('减弱动效', '降低动画与粒子效果（省电/防晕）', 'reduce_motion')
    ),
    h('div', { class: 'glass menu-list', style: { marginBottom: '14px' } },
      h('button', { class: 'menu-item', style: { width: '100%' }, onclick: () => nav('/blocks') }, '🙈 拉黑管理', h('span', { class: 'mi-arrow' }, '›')),
      h('button', { class: 'menu-item', style: { width: '100%' }, onclick: () => nav('/about/agreement') }, '📄 用户协议', h('span', { class: 'mi-arrow' }, '›')),
      h('button', { class: 'menu-item', style: { width: '100%' }, onclick: () => nav('/about/privacy') }, '🔒 隐私政策', h('span', { class: 'mi-arrow' }, '›')),
      h('button', { class: 'menu-item', style: { width: '100%' }, onclick: () => nav('/about/community') }, '🌱 社区规范', h('span', { class: 'mi-arrow' }, '›')),
      h('button', { class: 'menu-item', style: { width: '100%' }, onclick: () => nav('/about/minor') }, '🧒 未成年人保护', h('span', { class: 'mi-arrow' }, '›'))
    ),
    h('div', { class: 'glass menu-list' },
      h('button', {
        class: 'menu-item', style: { width: '100%' },
        onclick: () => { logout(); toast('已退出登录'); nav('/login'); }
      }, '👋 退出登录'),
      h('button', {
        class: 'menu-item', style: { width: '100%', color: 'var(--danger)' },
        onclick: () => confirmSheet('注销账号', '注销后账号无法恢复，资料将被匿名化处理。确定要离开句灵吗？', '确认注销', async () => {
          try {
            const { POST } = await import('../api.js');
            const r = await POST('/api/me/deactivate', { confirm: '确认注销' });
            toast(r.message);
            setToken(''); store.me = null;
            nav('/login');
          } catch (e) { toast(e.message, 'warn'); }
        })
      }, '⚠️ 注销账号')
    ),
    h('div', { class: 'notice-bar', style: { marginTop: '14px' } },
      store.boot?.compliance?.ai_notice || '', h('br'), store.boot?.compliance?.icp || '')
  );
}

export async function renderBlocks(page) {
  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', {}, h('h1', { style: { fontSize: '18px' } }, '拉黑管理')),
      h('div', { class: 'spacer' })
    )
  );
  const list = h('div', {});
  page.append(list);
  async function load() {
    list.innerHTML = '';
    const { items } = await GET('/api/me/blocks').catch(() => ({ items: [] }));
    if (!items.length) { list.append(emptyState('没有拉黑任何人', '世界清净又温柔')); return; }
    for (const u of items) {
      list.append(h('div', { class: 'glass menu-item', style: { marginBottom: '10px' } },
        avatarEl(u, 36),
        h('span', {}, u.nickname),
        h('button', {
          class: 'btn mini ghost', style: { marginLeft: 'auto' },
          onclick: async () => { try { await DEL(`/api/users/${u.id}/block`); toast('已解除拉黑'); load(); } catch (e) { toast(e.message, 'warn'); } }
        }, '解除')
      ));
    }
  }
  load();
}

const DOCS = {
  agreement: ['用户协议', `欢迎使用 AI句灵（下称"本应用"）。\n\n1. 你需要年满 14 周岁，未成年人应在监护人指导下使用。\n2. 你发布的内容应遵守法律法规与社区规范，不得发布违法、低俗、侵权内容。\n3. 本应用提供的 AI 生成内容（预览卡、动画、暖场互动）均会标识"AI 生成/AI 辅助生成"，仅供娱乐与创作参考。\n4. 虚拟商品（会员、皮肤、额度）一经购买不支持退款，法律法规另有规定除外。\n5. 我们有权对违规账号采取限制措施，并保留相关记录用于配合监管。\n\n（正式上线版本将由法务完善条款）`],
  privacy: ['隐私政策', `我们重视你的个人信息保护。\n\n1. 收集范围：账号信息（昵称/头像）、设备标识（游客登录）、你主动发布的内容、订单记录。\n2. 使用目的：提供社交与 AI 生成服务、内容审核、防刷与安全。\n3. AI 处理：你的文案会被发送至大模型服务商用于生成预览卡与动画指令；我们不会将其用于其他目的。\n4. 你可以在"设置"中注销账号，注销后资料将匿名化。\n5. 我们不会向第三方出售你的个人信息。\n\n（正式上线版本将按《个人信息保护法》完善并公示）`],
  community: ['社区规范', `句灵希望是一个温柔的角落。以下内容不被允许：\n\n· 色情低俗、暴力血腥\n· 赌博、诈骗、引导私下交易\n· 攻击辱骂、人肉搜索\n· 违法违规信息\n· 不适合未成年人的内容\n\n关于情绪表达：你可以难过，可以脆弱，句灵会接住你。但我们不允许美化、鼓励自伤行为。如果你正处在困境中，请拨打全国心理援助热线 12356，或联系信任的人。\n\n违规内容将被删除，严重者封禁账号。每个人都有"举报"按钮，感谢你一起守护句灵。`],
  minor: ['未成年人保护', `1. 本应用不向未满 14 周岁的儿童提供服务。\n2. 开启"青少年模式"后，全部消费功能将被关闭。\n3. 我们不向未成年人推送任何诱导消费的内容；AI 暖场官被禁止诱导任何用户充值。\n4. 如发现未成年人冒用成年人账号大额消费，监护人可联系客服处理退款事宜。\n5. 桌游玩法完全免费，不存在"付费变强"。`]
};

export function renderAbout(page, params) {
  const [title, body] = DOCS[params.doc] || ['说明', '文档不存在'];
  page.append(
    h('div', { class: 'topbar' },
      h('button', { class: 'icon-btn', onclick: () => history.back() }, '←'),
      h('div', {}, h('h1', { style: { fontSize: '18px' } }, title)),
      h('div', { class: 'spacer' })
    ),
    h('div', { class: 'glass card', style: { whiteSpace: 'pre-wrap', fontSize: '13.5px', lineHeight: 1.9, color: 'var(--ink-2)' } }, body)
  );
}
