// 解析历史本地缓存（与 history 云函数同步，本地作为快速缓存）
const KEY = 'parse_history';
const MAX = 200;

function list() {
  try {
    return wx.getStorageSync(KEY) || [];
  } catch (e) {
    return [];
  }
}

function save(arr) {
  try {
    wx.setStorageSync(KEY, arr.slice(0, MAX));
  } catch (e) {}
}

// 去重键：优先 rid，兼容早期无 rid 的旧记录
function keyOf(r) {
  return r.rid || `${r.platform}:${r.url || (r.images && r.images[0]) || ''}:${r.at}`;
}

function add(item) {
  const at = Date.now();
  const rec = {
    rid: item.rid || `${at}-${Math.random().toString(36).slice(2)}`,
    type: item.type,
    platform: item.platform,
    title: item.title || '',
    cover: item.cover || (item.images && item.images[0]) || '',
    url: item.url || '',
    images: item.images || [],
    imageFileIDs: item.imageFileIDs || [],
    fileID: item.fileID || '',
    at,
  };
  const arr = list();
  arr.unshift(rec);
  save(arr);
  return rec;
}

// 合并云端记录到本地（按 keyOf 去重，按时间倒序）
function merge(records) {
  const map = new Map();
  for (const r of list()) map.set(keyOf(r), r);
  for (const r of records || []) {
    if (r && !map.has(keyOf(r))) map.set(keyOf(r), r);
  }
  const arr = Array.from(map.values()).sort((a, b) => (b.at || 0) - (a.at || 0));
  save(arr);
  return arr;
}

function clear() {
  try {
    wx.removeStorageSync(KEY);
  } catch (e) {}
}

module.exports = { list, add, merge, clear };
