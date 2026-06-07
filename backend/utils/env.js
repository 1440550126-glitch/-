const fs=require('fs'); const path=require('path');
const envPath=path.join(process.cwd(),'.env'); if(fs.existsSync(envPath)){ for(const line of fs.readFileSync(envPath,'utf8').split(/\r?\n/)){ const m=line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)\s*$/); if(m && process.env[m[1]]===undefined) process.env[m[1]]=m[2].replace(/^['\"]|['\"]$/g,''); } }
function bool(name, fallback=false){ const v=process.env[name]; if(v===undefined) return fallback; return ['1','true','yes','on'].includes(String(v).toLowerCase()); }
function num(name, fallback=0){ const v=Number(process.env[name]); return Number.isFinite(v)?v:fallback; }
function str(name, fallback=''){ return process.env[name] || fallback; }
module.exports={bool,num,str,env:process.env};
