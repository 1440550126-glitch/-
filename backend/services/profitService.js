const {run,now}=require('../db'); const {id}=require('../utils/ids'); const {round}=require('../utils/money');
function record({userId,projectId=null,jobId=null,actualCost=0,userCharge=0}){ const gross=round(userCharge-actualCost); const margin=userCharge?round(gross/userCharge):0; run('INSERT INTO profit_logs (id,user_id,project_id,job_id,actual_cost,user_charge,gross_profit,profit_margin,created_at) VALUES (?,?,?,?,?,?,?,?,?)',[id('profit'),userId,projectId,jobId,actualCost,userCharge,gross,margin,now()]); return {gross,margin}; }
module.exports={record};
