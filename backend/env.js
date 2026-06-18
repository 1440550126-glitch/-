const fs = require('fs');
function loadEnv(file='.env'){ if(!fs.existsSync(file)) return; for(const line of fs.readFileSync(file,'utf8').split(/\r?\n/)){ const m=line.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/); if(m && process.env[m[1]]===undefined) process.env[m[1]]=m[2]; } }
loadEnv();
module.exports={loadEnv};
