const {num}=require('../utils/env');
function assertCanCall(taskType){ const assumed=num('VOLCENGINE_ACCOUNT_BALANCE_CNY',9999); if(assumed<num('VOLCENGINE_BALANCE_STOP_ALL_CNY',20)) throw new Error('provider_balance_stop_all'); if(taskType==='video_generation' && assumed<num('VOLCENGINE_BALANCE_PAUSE_VIDEO_CNY',50)) throw new Error('provider_balance_pause_video'); return {ok:true,assumed_balance_cny:assumed}; }
module.exports={assertCanCall};
