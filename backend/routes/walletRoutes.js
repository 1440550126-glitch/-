const express=require('../utils/miniExpress'); const {requireAuth}=require('../utils/security'); const wallet=require('../services/walletService'); const r=express.Router();
r.get('/',requireAuth,(req,res)=>res.json({wallet:wallet.ensureWallet(req.user.sub),transactions:wallet.transactions(req.user.sub)}));
module.exports=r;
