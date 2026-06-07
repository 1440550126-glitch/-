const { randomUUID } = require('crypto');
function id(prefix='id'){ return `${prefix}_${randomUUID().replace(/-/g,'').slice(0,24)}`; }
function code(len=8){ return Math.random().toString(36).slice(2,2+len).toUpperCase(); }
module.exports={id,code};
