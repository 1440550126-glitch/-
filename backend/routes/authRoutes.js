const express=require('../utils/miniExpress'); const ah=require('../utils/asyncHandler'); const auth=require('../services/authService'); const {requireAuth}=require('../utils/security'); const wallet=require('../services/walletService'); const r=express.Router();
r.post('/register',ah(async(req,res)=>res.json(auth.register(req.body.email,req.body.password,req.body.referral_code))));
r.post('/login',ah(async(req,res)=>res.json(auth.login(req.body.email,req.body.password))));
r.get('/me',requireAuth,ah(async(req,res)=>res.json({user:req.user,wallet:wallet.ensureWallet(req.user.sub)})));
r.get('/google/start',ah(async(req,res)=>res.redirect(await auth.googleStart())));
r.get('/google/callback',ah(async(req,res)=>{ const out=await auth.googleCallback(req.query); res.redirect(`/dashboard.html?token=${out.token}`); }));
module.exports=r;
