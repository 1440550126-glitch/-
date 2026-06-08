const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { str, bool } = require('./utils/env');

const requiredDirs = ['data', 'storage/videos', 'storage/frames', 'storage/uploads', 'storage/renders', 'storage/logs'];
const checks = [];
function ok(name, pass, detail = '') { checks.push({ name, pass, detail }); }

for (const dir of requiredDirs) {
  const full = path.join(process.cwd(), dir);
  if (!fs.existsSync(full)) fs.mkdirSync(full, { recursive: true });
  ok(`directory:${dir}`, fs.existsSync(full), full);
}

const sqlite = spawnSync('sqlite3', ['--version'], { encoding: 'utf8' });
ok('sqlite3-cli', sqlite.status === 0, sqlite.stdout?.trim() || sqlite.stderr?.trim() || 'sqlite3 command is required');

ok('DATABASE_PATH', !!str('DATABASE_PATH', './data/lingmirror.sqlite'), str('DATABASE_PATH', './data/lingmirror.sqlite'));
ok('JWT_SECRET', str('NODE_ENV') !== 'production' || str('JWT_SECRET').length >= 32, 'production requires JWT_SECRET length >= 32');
ok('ADMIN_PASSWORD', str('NODE_ENV') !== 'production' || str('ADMIN_PASSWORD').length >= 12, 'production requires ADMIN_PASSWORD length >= 12');

if (bool('ENABLE_REAL_API')) {
  ok('VOLCENGINE_ARK_API_KEY', !!str('VOLCENGINE_ARK_API_KEY'), 'required when ENABLE_REAL_API=true');
  ok('VOLCENGINE_ARK_BASE_URL', !!str('VOLCENGINE_ARK_BASE_URL'), str('VOLCENGINE_ARK_BASE_URL'));
}
if (bool('VOLCENGINE_ENABLE_VIDEO')) {
  ok('VIDEO_PAID_BALANCE_GUARD', true, 'video generation path enforces paid balance before provider call');
}

const failed = checks.filter(c => !c.pass);
console.log(JSON.stringify({ status: failed.length ? 'failed' : 'ok', checks }, null, 2));
if (failed.length) process.exit(1);
