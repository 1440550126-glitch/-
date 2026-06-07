function maskSecret(value){ if(!value) return ''; const s=String(value); return s.length<=8?'****':`${s.slice(0,4)}****${s.slice(-4)}`; }
function scrub(value){ let text=typeof value==='string'?value:JSON.stringify(value); ['VOLCENGINE_ARK_API_KEY','PAYPAL_CLIENT_SECRET','GOOGLE_CLIENT_SECRET','ALIPAY_PRIVATE_KEY','JWT_SECRET','ADMIN_PASSWORD'].forEach(k=>{ if(process.env[k]) text=text.replaceAll(process.env[k], maskSecret(process.env[k])); }); return text; }
function log(level,...args){ console.log(new Date().toISOString(), level, ...args.map(scrub)); }
module.exports={info:(...a)=>log('INFO',...a),warn:(...a)=>log('WARN',...a),error:(...a)=>log('ERROR',...a),maskSecret};
