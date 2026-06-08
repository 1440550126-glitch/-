const path=require('path'), fs=require('fs'), cp=require('child_process'); const {str}=require('./utils/env');
const dbPath=path.resolve(process.cwd(), str('DATABASE_PATH','./data/lingmirror.sqlite')); fs.mkdirSync(path.dirname(dbPath),{recursive:true});
function esc(v){ if(v===null||v===undefined) return 'NULL'; if(typeof v==='number') return String(v); return `'${String(v).replace(/'/g,"''")}'`; }
function q(sql,params=[]){ let i=0; return sql.replace(/\?/g,()=>esc(params[i++])); }
function raw(sql){ return cp.execFileSync('sqlite3',[dbPath,'-json',sql],{encoding:'utf8'}); }
function run(sql,params=[]){ const s=q(sql,params); cp.execFileSync('sqlite3',[dbPath,s]); return {changes:0}; }
function all(sql,params=[]){ const out=raw(q(sql,params)).trim(); return out?JSON.parse(out):[]; }
function get(sql,params=[]){ return all(sql,params)[0]; }
const db={exec:(sql)=>cp.execFileSync('sqlite3',[dbPath,sql]),transaction:(fn)=>(()=>fn())};
function now(){ return new Date().toISOString(); }
module.exports={db,all,get,run,now};
