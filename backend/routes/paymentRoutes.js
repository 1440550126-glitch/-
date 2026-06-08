const express=require('../utils/miniExpress'); const {requireAuth}=require('../utils/security'); const paypal=require('../services/paypalService'); const alipay=require('../services/alipayService'); const project=require('../services/projectService'); const ah=require('../utils/asyncHandler'); const r=express.Router();
r.post('/paypal/create-order',requireAuth,ah(async(req,res)=>res.json(await paypal.createOrder(req.user.sub,req.body.amount))));
r.post('/paypal/capture-order',requireAuth,ah(async(req,res)=>{ const o=await paypal.captureOrder(req.user.sub,req.body.orderId); res.json({order:o,resumed:project.autoResumePausedProjects(req.user.sub)}); }));
r.post('/alipay/create-order',requireAuth,ah(async(req,res)=>res.json(await alipay.createOrder(req.user.sub,req.body.amount))));
r.post('/alipay/notify',ah(async(req,res)=>res.send(await alipay.notify(req.body))));
r.get('/alipay/return',(req,res)=>res.redirect('/wallet.html'));
module.exports=r;
