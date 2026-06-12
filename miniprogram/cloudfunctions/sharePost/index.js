const { db, _ } = require('./common');
exports.main = async (event) => { await db.collection('shares').add({data:{user_id:event.user_id||'anonymous',post_id:event.post_id,created_at:Date.now()}}); await db.collection('posts').doc(event.post_id).update({data:{share_count:_.inc(1)}}); return {ok:true}; };
