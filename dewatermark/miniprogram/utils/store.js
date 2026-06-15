// 本地历史记录（仅存在用户本机，不上云）
const KEY = 'parse_history';
const MAX = 50;

function list() {
  try {
    return wx.getStorageSync(KEY) || [];
  } catch (e) {
    return [];
  }
}

function add(item) {
  const arr = list();
  const rec = {
    type: item.type,
    platform: item.platform,
    title: item.title || '',
    cover: item.cover || (item.images && item.images[0]) || '',
    url: item.url || '',
    images: item.images || [],
    imageFileIDs: item.imageFileIDs || [],
    fileID: item.fileID || '',
    at: Date.now(),
  };
  arr.unshift(rec);
  try {
    wx.setStorageSync(KEY, arr.slice(0, MAX));
  } catch (e) {}
  return rec;
}

function clear() {
  try {
    wx.removeStorageSync(KEY);
  } catch (e) {}
}

module.exports = { list, add, clear };
