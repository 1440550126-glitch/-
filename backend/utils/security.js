const crypto=require('crypto'); const {str}=require('./env');
function b64(o){ return Buffer.from(JSON.stringify(o)).toString('base64url'); }
function sign(user){ const payload={sub:user.id,email:user.email,plan:user.plan,role:user.role||'user',exp:Date.now()+7*864e5}; const body=b64(payload); const sig=crypto.createHmac('sha256',str('JWT_SECRET','dev-change-me')).update(body).digest('base64url'); return `${body}.${sig}`; }
function verify(token){ const [body,sig]=String(token||'').split('.'); const good=crypto.createHmac('sha256',str('JWT_SECRET','dev-change-me')).update(body).digest('base64url'); if(sig!==good) throw new Error('invalid_token'); const p=JSON.parse(Buffer.from(body,'base64url').toString()); if(p.exp<Date.now()) throw new Error('expired_token'); return p; }
function requireAuth(req,res,next){ const h=req.headers.authorization||''; const token=h.startsWith('Bearer ')?h.slice(7):''; if(!token) return res.status(401).json({error:'login_required'}); try{ req.user=verify(token); next(); }catch(e){ res.status(401).json({error:'invalid_token'}); } }
function optionalAuth(req,res,next){ const h=req.headers.authorization||''; if(h.startsWith('Bearer ')){ try{ req.user=verify(h.slice(7)); }catch(e){} } next(); }
function hashPassword(p){ const salt=crypto.randomBytes(12).toString('hex'); const h=crypto.scryptSync(p,salt,32).toString('hex'); return `${salt}:${h}`; }
function comparePassword(p,h){ if(!h) return false; const [salt,hash]=h.split(':'); return crypto.scryptSync(p,salt,32).toString('hex')===hash; }
function requireAdmin(req,res,next){ const p=req.headers['x-admin-password']; if(!str('ADMIN_PASSWORD') || p!==str('ADMIN_PASSWORD')) return res.status(403).json({error:'admin_password_required'}); next(); }
module.exports={sign,requireAuth,optionalAuth,hashPassword,comparePassword,requireAdmin};
