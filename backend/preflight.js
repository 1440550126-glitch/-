require('./env');
const fs = require('fs');
const required = ['PORT','HOST','DATABASE_PATH'];
const missing = required.filter(k => !process.env[k]);
if (missing.length && process.env.NODE_ENV === 'production') { console.warn('Missing optional/defaulted env:', missing.join(',')); }
if (process.env.VOLCENGINE_ARK_API_KEY && process.env.VOLCENGINE_ARK_API_KEY.length < 8) throw new Error('VOLCENGINE_ARK_API_KEY looks invalid');
if (fs.existsSync('.env') && !fs.readFileSync('.gitignore','utf8').includes('.env')) throw new Error('.env must be ignored');
console.log('Preflight OK: LingMirror AI v1.0 LTS 商用冻结版');
