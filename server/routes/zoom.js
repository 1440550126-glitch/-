// 句灵·无限放大：从一句话/情绪逐层放大，AI 现生成更深一层的「世界帧」
import { POST } from '../lib/httpx.js';
import { generateFrame } from '../lib/zoom.js';

POST('/api/zoom', async (ctx) => {
  const path = Array.isArray(ctx.body.path) ? ctx.body.path.slice(-8).map((s) => String(s).slice(0, 24)) : [];
  const focus = (String(ctx.body.focus || ctx.body.seed || '此刻').slice(0, 40).trim()) || '此刻';
  const frame = await generateFrame({ path, focus, userId: ctx.user.id });
  return { frame };
}, { auth: true });
