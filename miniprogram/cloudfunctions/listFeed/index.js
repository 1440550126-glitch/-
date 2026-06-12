const { db } = require('./common');
exports.main = async (event) => { const res=await db.collection('posts').where({status:'published'}).orderBy(event.sort==='hot'?'play_count':'created_at','desc').limit(event.limit||30).get(); return res.data; };
