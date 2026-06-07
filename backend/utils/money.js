function cents(amount){ return Math.round(Number(amount || 0) * 100); }
function dollars(c){ return Math.round(Number(c || 0)) / 100; }
function round(amount){ return Math.round(Number(amount || 0) * 100) / 100; }
module.exports={cents,dollars,round};
