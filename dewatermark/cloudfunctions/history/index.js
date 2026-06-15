const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

const COL = 'histories';

function cleanRecord(r, openid) {
  return {
    openid,
    rid: String(r.rid),
    type: r.type || 'video',
    platform: r.platform || 'unknown',
    title: r.title || '',
    cover: r.cover || '',
    url: r.url || '',
    images: Array.isArray(r.images) ? r.images.slice(0, 30) : [],
    imageFileIDs: Array.isArray(r.imageFileIDs) ? r.imageFileIDs.slice(0, 30) : [],
    fileID: r.fileID || '',
    at: r.at || Date.now(),
  };
}

function strip(d) {
  const { _id, openid, ...rest } = d;
  return rest;
}

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  const action = event.action || 'list';
  const col = db.collection(COL);

  try {
    if (action === 'add') {
      const r = event.record || {};
      if (!r.rid) return { ok: false, msg: 'missing rid' };
      // 按 (openid, rid) 去重，已存在则跳过
      const exist = await col.where({ openid: OPENID, rid: String(r.rid) }).count();
      if (exist.total === 0) await col.add({ data: cleanRecord(r, OPENID) });
      return { ok: true };
    }

    if (action === 'list') {
      const limit = Math.min(event.limit || 100, 100);
      const res = await col.where({ openid: OPENID }).orderBy('at', 'desc').limit(limit).get();
      return { ok: true, list: res.data.map(strip) };
    }

    if (action === 'clear') {
      const r = await col.where({ openid: OPENID }).remove();
      return { ok: true, removed: (r.stats && r.stats.removed) || 0 };
    }

    return { ok: false, msg: 'unknown action' };
  } catch (e) {
    // 集合不存在或其它异常：返回失败但不抛，前端继续用本地缓存
    return { ok: false, msg: String((e && e.message) || e) };
  }
};
