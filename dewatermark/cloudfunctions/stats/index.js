const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();
const _ = db.command;
const $ = db.command.aggregate;

function startOfToday() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

async function safe(promise, dflt) {
  try {
    return await promise;
  } catch (e) {
    return dflt;
  }
}

function countAll(col) {
  return safe(db.collection(col).count().then((r) => r.total), 0);
}
function countWhere(col, where) {
  return safe(db.collection(col).where(where).count().then((r) => r.total), 0);
}

exports.main = async () => {
  const { OPENID } = cloud.getWXContext();

  // 管理员白名单：在 stats 云函数环境变量 ADMIN_OPENIDS 里配置（逗号分隔）
  const admins = (process.env.ADMIN_OPENIDS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  if (!admins.length) return { ok: false, code: 'NO_ADMIN', msg: '尚未配置管理员', openid: OPENID };
  if (!admins.includes(OPENID)) return { ok: false, code: 'FORBIDDEN', msg: '当前账号无权限', openid: OPENID };

  const today = startOfToday();
  const d7 = today - 6 * 86400000;

  const [pTotal, pToday, p7] = await Promise.all([
    countAll('parse_logs'),
    countWhere('parse_logs', { created_at: _.gte(today) }),
    countWhere('parse_logs', { created_at: _.gte(d7) }),
  ]);

  const byPlatform = await safe(
    db
      .collection('parse_logs')
      .aggregate()
      .group({ _id: '$platform', n: $.sum(1) })
      .end()
      .then((r) => (r.list || []).map((x) => ({ key: x._id || 'unknown', n: x.n })).sort((a, b) => b.n - a.n)),
    []
  );

  const byVia = await safe(
    db
      .collection('parse_logs')
      .aggregate()
      .group({ _id: '$via', n: $.sum(1) })
      .end()
      .then((r) => (r.list || []).map((x) => ({ key: x._id || 'unknown', n: x.n }))),
    []
  );

  const [uTotal, uNewToday, uActiveToday, uActive7] = await Promise.all([
    countAll('users'),
    countWhere('users', { created_at: _.gte(today) }),
    countWhere('users', { last_at: _.gte(today) }),
    countWhere('users', { last_at: _.gte(d7) }),
  ]);

  // 复访用户：最近活跃比首次访问晚 ≥ 1 天（聚合表达式，失败降级为 null 由前端隐藏）
  const returned = await safe(
    db
      .collection('users')
      .aggregate()
      .match(_.expr($.gte([$.subtract(['$last_at', '$created_at']), 86400000])))
      .count('n')
      .end()
      .then((r) => (r.list && r.list[0] && r.list[0].n) || 0),
    null
  );

  return {
    ok: true,
    generatedAt: Date.now(),
    parse: { total: pTotal, today: pToday, last7: p7, byPlatform, byVia },
    user: {
      total: uTotal,
      newToday: uNewToday,
      activeToday: uActiveToday,
      active7: uActive7,
      returned,
      returnRate: returned != null && uTotal ? Math.round((returned / uTotal) * 100) : null,
    },
  };
};
