// 全局状态：我、启动常量、皮肤目录（payload 查表用）
import { GET, POST, getToken, setToken } from './api.js';

export const store = {
  me: null,
  boot: null,          // /api/bootstrap：头像、会员方案、举报原因、合规信息
  skins: new Map(),    // skinId -> {type, payload, name, rarity}
  topic: null
};

export function deviceId() {
  let id = localStorage.getItem('jl_device');
  if (!id) {
    id = 'dev_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('jl_device', id);
  }
  return id;
}

export async function loadBoot() {
  if (!store.boot) store.boot = await GET('/api/bootstrap');
  try {
    const cat = await GET('/api/shop/catalog');
    store.skins = new Map(cat.skins.map((s) => [s.id, s]));
  } catch { /* 商城目录失败不阻塞启动 */ }
  return store.boot;
}

export async function refreshMe() {
  if (!getToken()) { store.me = null; return null; }
  try { store.me = await GET('/api/me'); } catch { store.me = null; setToken(''); }
  return store.me;
}

export async function guestLogin() {
  const data = await POST('/api/auth/guest', { device_id: deviceId() });
  setToken(data.token);
  store.me = data.user;
  if (data.device_id) localStorage.setItem('jl_device', data.device_id);
  return store.me;
}

export const isMember = () => !!store.me?.is_member;
export const avatarMeta = (id) => store.boot?.avatars?.find((a) => a.id === id) || { colors: ['#ddd', '#bbb'], face: '· ·', name: '句灵' };
export const skinPayload = (id) => store.skins.get(id)?.payload || null;
export const logout = () => { setToken(''); store.me = null; };
