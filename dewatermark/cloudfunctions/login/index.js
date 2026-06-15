const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async () => {
  const { OPENID } = cloud.getWXContext();
  try {
    const users = db.collection('users');
    const r = await users.where({ openid: OPENID }).count();
    if (r.total === 0) {
      await users.add({ data: { openid: OPENID, created_at: Date.now(), last_at: Date.now() } });
    } else {
      await users.where({ openid: OPENID }).update({ data: { last_at: Date.now() } });
    }
  } catch (e) {
    // 集合未创建时忽略，不影响登录
  }
  return { openid: OPENID };
};
