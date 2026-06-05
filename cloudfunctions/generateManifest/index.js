const { parse } = require('./common');
exports.main = async (event) => { const result = parse(event.text, event.emotionTag, event.theme).animation_manifest; result.post_id = event.post_id || ''; return result; };
