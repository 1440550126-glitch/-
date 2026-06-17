// cloudfunctions/coupleData/index.js — 情侣关系与共享数据同步（云端权威合并方）
//
// actions:
//   bind   : code 为空 → 生成邀请码并建立关系（等待对方）；有 code → 用对方邀请码加入
//   pull   : 拉取本情侣的共享快照（首次启动用，不上传本地）
//   sync   : 上传本地快照 → 与云端合并保存 → 返回合并结果（云端为权威方）
//   unbind : 退出关系（仅剩自己则删除整条关系）
//
// 数据：集合 couples = { _id, members:[openid...], inviteCode, sync:{data,meta,tomb}, updatedAt }
// 鉴权：所有操作以调用者 OPENID 为准，仅能操作"自己所属"的关系。
// 部署前请在云开发控制台创建集合 couples（云函数以管理员身份读写，集合权限可设"仅管理端"）。

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();
const _ = db.command;
const couples = db.collection('couples');

const EMPTY = { data: {}, meta: {}, tomb: {} };

function code6() {
  const s = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // 去掉易混字符 I/O/0/1
  let c = '';
  for (let i = 0; i < 6; i++) c += s[Math.floor(Math.random() * s.length)];
  return c;
}

// 按 id 合并两个数组：保留两边所有唯一 id（不丢新增）；id 冲突时取"较新一方"；剔除墓碑 id
function unionById(a, b, bNewer, tomb) {
  const older = bNewer ? (a || []) : (b || []);
  const newer = bNewer ? (b || []) : (a || []);
  const m = {};
  older.forEach(x => { if (x && x.id != null) m[x.id] = x; });
  newer.forEach(x => { if (x && x.id != null) m[x.id] = x; });
  const t = tomb || [];
  return Object.keys(m).map(k => m[k]).filter(x => t.indexOf(x.id) < 0);
}

// 按作者合并 { date, byAuthor:{openid:值} }：不同日期取较新日期的整条；同一天并集 byAuthor（同作者取较新一方）
function mergeAuthorMap(a, b, bNewer) {
  if (!a) return b; if (!b) return a;
  if (a.date !== b.date) return (String(b.date) > String(a.date)) ? b : a;
  const older = bNewer ? a : b, newer = bNewer ? b : a;
  const out = Object.assign({}, older, newer);
  out.byAuthor = Object.assign({}, older.byAuthor || {}, newer.byAuthor || {});
  return out;
}

function mergeDocs(base, inc) {
  base = base || EMPTY; inc = inc || EMPTY;
  const bd = base.data || {}, id = inc.data || {}, bm = base.meta || {}, im = inc.meta || {}, bt = base.tomb || {}, it = inc.tomb || {};
  const out = { data: {}, meta: {}, tomb: {} };
  // 墓碑并集（先算，供数组合并剔除）
  const tk = {}; Object.keys(bt).forEach(k => tk[k] = 1); Object.keys(it).forEach(k => tk[k] = 1);
  Object.keys(tk).forEach(k => {
    const s = {}; (bt[k] || []).concat(it[k] || []).forEach(v => s[v] = 1);
    out.tomb[k] = Object.keys(s).map(n => (n !== '' && !isNaN(n)) ? Number(n) : n);
  });
  // 数据合并：数组按 id 并集，其余按时间戳取新
  const ks = {}; Object.keys(bd).forEach(k => ks[k] = 1); Object.keys(id).forEach(k => ks[k] = 1);
  Object.keys(ks).forEach(key => {
    const bv = bm[key] || 0, iv = im[key] || 0, bval = bd[key], ival = id[key];
    if (Array.isArray(bval) || Array.isArray(ival)) {
      out.data[key] = unionById(bval, ival, iv >= bv, out.tomb[key] || []);
    } else if ((bval && bval.byAuthor) || (ival && ival.byAuthor)) {
      out.data[key] = mergeAuthorMap(bval, ival, iv >= bv);     // 心情/每日一问：按作者并集
    } else {
      out.data[key] = iv >= bv ? (ival !== undefined ? ival : bval) : (bval !== undefined ? bval : ival);
    }
    out.meta[key] = Math.max(bv, iv);
  });
  return out;
}

async function myCouple(openid) {
  const r = await couples.where({ members: openid }).limit(1).get();
  return r.data && r.data[0];
}

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  if (!OPENID) return { ok: false, error: 'NO_OPENID' };
  const action = event && event.action;

  try {
    if (action === 'bind') {
      const existing = await myCouple(OPENID);
      if (existing) {
        return { ok: true, coupleId: existing._id, inviteCode: existing.inviteCode, role: existing.members[0] === OPENID ? 'initiator' : 'member', openid: OPENID, joined: existing.members.length >= 2, doc: existing.sync || EMPTY };
      }
      const code = (event.code || '').trim().toUpperCase();
      if (code) {
        const found = await couples.where({ inviteCode: code }).limit(1).get();
        const target = found.data && found.data[0];
        if (!target) return { ok: false, error: 'CODE_NOT_FOUND' };
        if (target.members.indexOf(OPENID) < 0) {
          if (target.members.length >= 2) return { ok: false, error: 'COUPLE_FULL' };
          await couples.doc(target._id).update({ data: { members: _.addToSet(OPENID), updatedAt: Date.now() } });
        }
        const fresh = await couples.doc(target._id).get();
        return { ok: true, coupleId: target._id, inviteCode: target.inviteCode, role: 'member', openid: OPENID, joined: (fresh.data.members || []).length >= 2, doc: fresh.data.sync || EMPTY };
      }
      const add = await couples.add({ data: { members: [OPENID], inviteCode: code6(), sync: EMPTY, createdAt: Date.now(), updatedAt: Date.now() } });
      const created = await couples.doc(add._id).get();
      return { ok: true, coupleId: add._id, inviteCode: created.data.inviteCode, role: 'initiator', openid: OPENID, joined: false, doc: EMPTY };
    }

    if (action === 'pull') {
      const c = await myCouple(OPENID);
      if (!c) return { ok: false, error: 'NOT_BOUND' };
      return { ok: true, doc: c.sync || EMPTY, inviteCode: c.inviteCode, joined: c.members.length >= 2, updatedAt: c.updatedAt || 0 };
    }

    // 轻量探测：只回 updatedAt，供客户端判断"对方是否有更新"（准实时轮询用）
    if (action === 'ping') {
      const c = await myCouple(OPENID);
      if (!c) return { ok: false, error: 'NOT_BOUND' };
      return { ok: true, updatedAt: c.updatedAt || 0, joined: (c.members || []).length >= 2 };
    }

    if (action === 'sync') {
      const c = await myCouple(OPENID);
      if (!c) return { ok: false, error: 'NOT_BOUND' };
      const ua = Date.now();
      const merged = mergeDocs(c.sync || EMPTY, event.payload || EMPTY);
      await couples.doc(c._id).update({ data: { sync: merged, updatedAt: ua } });
      return { ok: true, doc: merged, inviteCode: c.inviteCode, joined: c.members.length >= 2, updatedAt: ua };
    }

    if (action === 'unbind') {
      const c = await myCouple(OPENID);
      if (c) {
        if ((c.members || []).length <= 1) await couples.doc(c._id).remove();
        else await couples.doc(c._id).update({ data: { members: _.pull(OPENID), updatedAt: Date.now() } });
      }
      return { ok: true };
    }

    return { ok: false, error: 'UNKNOWN_ACTION' };
  } catch (e) {
    return { ok: false, error: (e && (e.errMsg || e.message)) || String(e) };
  }
};
