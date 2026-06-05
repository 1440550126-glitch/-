const { moderate } = require('./common');
exports.main = async (event) => moderate(event.text);
