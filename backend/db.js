const path = require('path');
const fs = require('fs');
const { execFile } = require('child_process');
require('./env');
const dbPath = process.env.DATABASE_PATH || './data/lingmirror.sqlite';
fs.mkdirSync(path.dirname(dbPath), { recursive: true });
function esc(v){ if(v===null||v===undefined) return 'NULL'; if(typeof v==='number') return Number.isFinite(v)?String(v):'NULL'; return `'${String(v).replace(/'/g,"''")}'`; }
function fmt(sql, params=[]){ let i=0; return sql.replace(/\?/g,()=>esc(params[i++])); }
function exec(sql){ return new Promise((resolve,reject)=>{ execFile('sqlite3',[dbPath,sql],{maxBuffer:1024*1024*10},(err,stdout,stderr)=>err?reject(new Error(stderr||err.message)):resolve(stdout)); }); }
async function run(sql, params=[]){ const out=await exec(`${fmt(sql,params)}; SELECT changes() || ',' || last_insert_rowid();`); const last=out.trim().split(/\r?\n/).pop() || '0,0'; const [changes,lastID]=last.split(',').map(Number); return {changes:changes||0,lastID:lastID||0}; }
async function all(sql, params=[]){ const out=await new Promise((resolve,reject)=>{ execFile('sqlite3',['-json',dbPath,fmt(sql,params)],{maxBuffer:1024*1024*20},(err,stdout,stderr)=>err?reject(new Error(stderr||err.message)):resolve(stdout)); }); return out.trim()?JSON.parse(out):[]; }
async function get(sql, params=[]){ return (await all(sql,params))[0]; }
module.exports = { run, get, all, dbPath };
