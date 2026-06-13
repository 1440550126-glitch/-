// 凶夜赛季通行证：进度 + 奖励轨道 + 领取（解锁高级档走商城订单流，见 shop.js kind='season'）
import { GET, POST, bad } from '../lib/httpx.js';
import { seasonStateFor, claimReward } from '../lib/season.js';

GET('/api/season', async (ctx) => seasonStateFor(ctx.user.id), { auth: true });

POST('/api/season/claim', async (ctx) => {
  const r = claimReward(ctx.user.id, ctx.body.level, ctx.body.track);
  if (!r.ok) throw bad(r.error, r.need_premium ? { need_premium: true } : undefined);
  return { done: true, skin: r.skin };
}, { auth: true });
