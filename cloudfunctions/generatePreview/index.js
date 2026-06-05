const { parse } = require('./common');
exports.main = async (event) => parse(event.text, event.emotionTag, event.theme).preview_config;
