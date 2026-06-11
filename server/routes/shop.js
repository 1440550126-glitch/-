import { GET, POST, bad, notFound, denied } from '../lib/httpx.js';
import { q, tx } from '../lib/db.js';
import { now, uid, jparse } from '../lib/util.js';
import { MEMBER_PLANS, MEMBER_BENEFITS, CREDIT_PACKS } from '../lib/catalog.js';
import { isMember } from '../lib/auth.js';
import { meView } from './auth.js';

// 商城目录：皮肤 + 会员 + 高级额度（全部纯外观/纯功能解锁，不卖任何对局优势）
GET('/api/shop/catalog', async (ctx) => {
  const skins = q.all('SELECT * FROM skins WHERE enabled = 1 ORDER BY sort, price_fen');
  const owned = ctx.user
    ? new Set(q.all('SELECT skin_id FROM user_skins WHERE user_id = ?', ctx.user.id).map((r) => r.skin_id))
    : new Set();
  return {
    skins: skins.map((s) => ({ ...s, payload: jparse(s.payload, {}), owned: owned.has(s.id) || s.price_fen === 0 })),
    member_plans: MEMBER_PLANS,
    member_benefits: MEMBER_BENEFITS,
    credit_packs: CREDIT_PACKS,
    me: ctx.user ? { is_member: isMember(ctx.user), member_until: ctx.user.member_until, credits: ctx.user.credits, equipped: jparse(ctx.user.equipped, {}) } : null,
    fair_play: '所有皮肤仅改变外观，不影响任何玩法与公平性；不向未成年人提供付费服务。'
  };
});

POST('/api/shop/orders', async (ctx) => {
  const { kind, item_id } = ctx.body;
  if (jparse(ctx.user.settings, {}).teen_mode) {
    throw denied('青少年模式下无法购买。健康上网，快乐成长 💚');
  }
  let title = ''; let amount = 0;
  if (kind === 'member') {
    const plan = MEMBER_PLANS.find((p) => p.id === item_id);
    if (!plan) throw bad('会员方案不存在');
    title = plan.name; amount = plan.price_fen;
  } else if (kind === 'skin') {
    const skin = q.get('SELECT * FROM skins WHERE id = ? AND enabled = 1', String(item_id));
    if (!skin) throw notFound('皮肤不存在或已下架');
    if (skin.price_fen === 0) throw bad('免费皮肤无需购买，直接装备即可');
    if (q.get('SELECT 1 x FROM user_skins WHERE user_id = ? AND skin_id = ?', ctx.user.id, skin.id)) throw bad('你已经拥有这款皮肤啦');
    title = `${skin.name}（${skin.type === 'card_frame' ? '卡片边框' : skin.type === 'avatar_frame' ? '头像框' : skin.type === 'bubble' ? '聊天气泡' : skin.type === 'anim_fx' ? '动画特效' : '房间主题'}）`;
    amount = skin.price_fen;
  } else if (kind === 'credits') {
    const pack = CREDIT_PACKS.find((p) => p.id === item_id);
    if (!pack) throw bad('额度包不存在');
    title = pack.name; amount = pack.price_fen;
  } else {
    throw bad('订单类型无效');
  }
  const id = uid('ord_', 14);
  q.run(
    'INSERT INTO orders (id, user_id, kind, item_id, title, amount_fen, status, channel, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
    id, ctx.user.id, kind, String(item_id), title, amount, 'pending', 'sandbox', now()
  );
  return {
    order: { id, kind, item_id, title, amount_fen: amount, status: 'pending' },
    pay_hint: '当前为沙盒支付环境。正式上线将接入微信支付/支付宝，iOS 内购买虚拟商品走 Apple 内购（IAP）。'
  };
}, { auth: true });

// 沙盒支付回调（生产替换为微信/支付宝/Apple IAP 的服务端回调，逻辑完全一致：验单→入账→发货）
POST('/api/shop/orders/:id/pay', async (ctx) => {
  const order = q.get('SELECT * FROM orders WHERE id = ? AND user_id = ?', ctx.params.id, ctx.user.id);
  if (!order) throw notFound('订单不存在');
  if (order.status === 'paid') return { order, message: '订单已支付' };
  if (order.status !== 'pending') throw bad('订单状态异常');

  tx(() => {
    q.run("UPDATE orders SET status = 'paid', paid_at = ? WHERE id = ?", now(), order.id);
    if (order.kind === 'member') {
      const plan = MEMBER_PLANS.find((p) => p.id === order.item_id);
      const base = Math.max(ctx.user.member_until, now());
      q.run('UPDATE users SET member_until = ? WHERE id = ?', base + plan.months * 30 * 86400_000, ctx.user.id);
    } else if (order.kind === 'skin') {
      q.run('INSERT OR IGNORE INTO user_skins (user_id, skin_id, created_at) VALUES (?,?,?)', ctx.user.id, order.item_id, now());
    } else if (order.kind === 'credits') {
      const pack = CREDIT_PACKS.find((p) => p.id === order.item_id);
      q.run('UPDATE users SET credits = credits + ? WHERE id = ?', pack.credits, ctx.user.id);
      q.run('INSERT INTO credit_logs (user_id, delta, reason, ref, created_at) VALUES (?,?,?,?,?)',
        ctx.user.id, pack.credits, `购买${pack.name}`, order.id, now());
    }
  });
  const fresh = q.get('SELECT * FROM users WHERE id = ?', ctx.user.id);
  return { order: { ...order, status: 'paid' }, me: meView(fresh), message: '支付成功！' };
}, { auth: true });

GET('/api/me/orders', async (ctx) => {
  return { items: q.all('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 50', ctx.user.id) };
}, { auth: true });

GET('/api/me/skins', async (ctx) => {
  const rows = q.all(
    `SELECT s.*, us.created_at acquired_at FROM user_skins us JOIN skins s ON s.id = us.skin_id WHERE us.user_id = ?`,
    ctx.user.id
  );
  const free = q.all('SELECT * FROM skins WHERE enabled = 1 AND price_fen = 0');
  const all = [...rows, ...free.filter((f) => !rows.some((r) => r.id === f.id))];
  return { items: all.map((s) => ({ ...s, payload: jparse(s.payload, {}) })), equipped: jparse(ctx.user.equipped, {}) };
}, { auth: true });

POST('/api/me/equip', async (ctx) => {
  const { type, skin_id } = ctx.body;
  const valid = ['card_frame', 'avatar_frame', 'bubble', 'anim_fx', 'room_theme'];
  if (!valid.includes(type)) throw bad('皮肤槽位无效');
  const equipped = jparse(ctx.user.equipped, {});
  if (skin_id == null) {
    delete equipped[type];
  } else {
    const skin = q.get('SELECT * FROM skins WHERE id = ? AND enabled = 1', String(skin_id));
    if (!skin || skin.type !== type) throw bad('皮肤不存在');
    const owned = skin.price_fen === 0 || q.get('SELECT 1 x FROM user_skins WHERE user_id = ? AND skin_id = ?', ctx.user.id, skin.id);
    if (!owned) throw denied('先拥有这款皮肤才能装备哦');
    equipped[type] = skin.id;
  }
  q.run('UPDATE users SET equipped = ? WHERE id = ?', JSON.stringify(equipped), ctx.user.id);
  return { equipped };
}, { auth: true });
