const { run } = require('./db');
(async () => {
  await run('PRAGMA journal_mode=WAL');
  await run(`CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT,google_sub TEXT,display_name TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)`);
  await run(`CREATE TABLE IF NOT EXISTS wallets (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER UNIQUE NOT NULL,current_balance REAL DEFAULT 0,paid_balance REAL DEFAULT 0,bonus_balance REAL DEFAULT 0,frozen_balance REAL DEFAULT 0,spent_total REAL DEFAULT 0,updated_at TEXT DEFAULT CURRENT_TIMESTAMP)`);
  await run(`CREATE TABLE IF NOT EXISTS wallet_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,type TEXT NOT NULL,bucket TEXT NOT NULL,amount REAL NOT NULL,description TEXT,provider TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)`);
  await run(`CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,title TEXT NOT NULL,type TEXT DEFAULT 'video',status TEXT DEFAULT 'pending',estimated_cost REAL DEFAULT 0,paid_required INTEGER DEFAULT 0,result_json TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP)`);
  await run(`CREATE TABLE IF NOT EXISTS api_usage_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,project_id INTEGER,module TEXT,provider TEXT,model TEXT,gateway_used INTEGER DEFAULT 0,fallback_used INTEGER DEFAULT 0,input_tokens INTEGER DEFAULT 0,output_tokens INTEGER DEFAULT 0,estimated_cost REAL DEFAULT 0,actual_cost REAL DEFAULT 0,user_charge REAL DEFAULT 0,profit REAL DEFAULT 0,profit_margin REAL DEFAULT 0,error_message TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)`);
  await run(`CREATE TABLE IF NOT EXISTS project_memory_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL,user_id INTEGER NOT NULL,snapshot_json TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)`);
  await run(`CREATE TABLE IF NOT EXISTS memory_anchors (id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER,user_id INTEGER NOT NULL,title TEXT,content TEXT,provider TEXT,model TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)`);
  await run(`CREATE TABLE IF NOT EXISTS generation_jobs (id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER,user_id INTEGER NOT NULL,module TEXT,status TEXT DEFAULT 'pending',provider TEXT,model TEXT,fallback_used INTEGER DEFAULT 0,result_json TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP)`);
  await run(`CREATE TABLE IF NOT EXISTS admin_audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,action TEXT,details TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)`);
  console.log('Migration complete');
})().catch((e) => { console.error(e); process.exit(1); });
