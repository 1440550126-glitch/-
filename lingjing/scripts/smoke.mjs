#!/usr/bin/env node
// 灵境AI · 冒烟测试：API 全链路 + Agent API + MCP stdio（零依赖，临时库，不污染数据）
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const PORT = 4519;
const BASE = `http://127.0.0.1:${PORT}`;
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'ql-smoke-'));

let passed = 0;
let failed = 0;
const ok = (cond, name) => {
  if (cond) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.error(`  ✗ ${name}`); }
};

const server = spawn(process.execPath, ['--disable-warning=ExperimentalWarning', path.join(ROOT, 'server', 'index.js')], {
  env: { ...process.env, LINGJING_PORT: PORT, LINGJING_DB_PATH: path.join(TMP, 'db.sqlite'), LINGJING_UPLOAD_DIR: path.join(TMP, 'up'), LINGJING_FAST_LOCAL: '1', ARK_API_KEY: '' },
  stdio: ['ignore', 'pipe', 'pipe']
});
server.stderr.on('data', (d) => process.env.SMOKE_VERBOSE && console.error(String(d)));

async function until(fn, ms = 8000) {
  const t0 = Date.now();
  for (;;) {
    try { const r = await fn(); if (r) return r; } catch { /* retry */ }
    if (Date.now() - t0 > ms) throw new Error('timeout');
    await new Promise((r) => setTimeout(r, 150));
  }
}
async function api(method, p, body, token) {
  const res = await fetch(BASE + p, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, ...json };
}

try {
  console.log('\n— 实体跨桶去重（单元） —');
  // 隔离临时库导入流水线，验证「同名同时出现在 characters 与 props」时只保留道具、人物里不残留
  process.env.LINGJING_DB_PATH = path.join(TMP, 'unit.sqlite');
  process.env.LINGJING_UPLOAD_DIR = path.join(TMP, 'unit-up');
  const { normalizeStoryboard } = await import(path.join(ROOT, 'server', 'lib', 'pipeline.js'));
  // 模拟大模型把「能源核心」既塞进角色（还瞎填了性别/拟人描述）又塞进道具的脏数据
  const dupSb = normalizeStoryboard({
    title: '去重测试', style: '电影写实',
    characters: [
      { key: 'c1', name: '林夏', role: '主角', gender: '女', desc: '28岁女性，干练短发，沉着冷静' },
      { key: 'c2', name: '能源核心', role: '配角', gender: '女', desc: '散发蓝光、低声嗡鸣的神秘存在' }
    ],
    scenes: [{ key: 's1', name: '主控室', desc: '冷色调机房' }],
    props: [{ key: 'p1', name: '能源核心', desc: '蓝色晶体反应堆核心' }],
    shots: [{ key: 'sh1', order: 1, scene: 's1', characters: ['c1', 'c2'], action: '林夏注视能源核心' }]
  });
  const charNames = dupSb.characters.map((c) => c.name);
  const propNames = dupSb.props.map((p) => p.name);
  ok(!charNames.includes('能源核心'), '跨桶去重：道具不再残留在人物列表');
  ok(propNames.filter((n) => n === '能源核心').length === 1, '跨桶去重：道具在道具列表中仅一份');
  ok(charNames.includes('林夏'), '跨桶去重：真人角色保留');
  // 分镜对已移除角色的引用应被清掉，不留悬空 key
  const c2gone = !dupSb.characters.some((c) => c.name === '能源核心');
  const danglingRef = dupSb.shots.some((sh) => (sh.characters || []).some((k) => !dupSb.characters.find((c) => c.key === k)));
  ok(c2gone && !danglingRef, '跨桶去重：分镜不残留悬空角色引用');
  // 总控/摄影机参数随片：图与视频提示词都应带【细节】摄影机参数 + 抗畸变 + 该镜角色锁定档案
  const vprompt = dupSb.shots[0].video_prompt || '';
  const iprompt = dupSb.shots[0].image_prompt || '';
  ok(/【摄影机】/.test(vprompt) && /定焦/.test(vprompt) && /光圈|景深/.test(vprompt) && /mm/.test(vprompt), '视频提示词含细节摄影机参数（机身/镜头/光圈/景深）');
  ok(/畸变|比例真实/.test(vprompt), '视频提示词含抗失真/抗畸变约束');
  ok(/【摄影机】/.test(iprompt) && /定焦/.test(iprompt) && /畸变|比例真实/.test(iprompt), '首帧图提示词也含细节摄影机参数与抗畸变');
  ok(/角色锁定/.test(vprompt) && vprompt.includes('林夏') && /固定不变/.test(vprompt), '视频提示词含角色锁定档案（总控随片，防变形/换人/身高突变）');
  // 写实画风应点名真实电影摄影机机身
  ok(/ARRI|电影摄影机/.test(vprompt), '写实画风点名真实电影摄影机机身');
  // 角色定义图升级为三视图设定图（正/侧/背），全片定海神针参考
  ok(/三视图/.test(dupSb.characters[0].image_prompt || ''), '角色定义图为三视图设定图（正面·侧面·背面）');
  // 借鉴"身份板"：角色参考升级为角色设定板（结构化标注 + 多姿态 + 表情研究 + 细节研究）+ 视觉签名锚点
  ok(/角色设定板/.test(dupSb.characters[0].image_prompt) && /视觉签名/.test(dupSb.characters[0].image_prompt) && /表情研究/.test(dupSb.characters[0].image_prompt), '角色参考升级为身份板（标注+多姿态+表情研究+细节）');
  ok(/视觉签名\(必出特征\)/.test(dupSb.characters[0].lock) && /短发/.test(dupSb.characters[0].lock), '锁定档案含视觉签名（必出识别特征锚点）');
  ok(/视觉签名/.test(dupSb.shots[0].image_prompt), '视觉签名随锁定档案进入每个分镜（复杂景别下仍锁角色）');
  // 多供应商：按模型 ID 路由（OpenAI GPT Image / Google Veo 3 / 火山方舟），未配 Key 时不启用
  const prov = await import(path.join(ROOT, 'server', 'lib', 'providers.js'));
  ok(prov.imageProviderOf('gpt-image-1') === 'openai' && prov.imageProviderOf('doubao-seedream-4-0-250828') === 'ark', '图像供应商按模型ID路由（gpt-image→openai）');
  ok(prov.videoProviderOf('veo-3.0-generate-001') === 'google' && prov.videoProviderOf('doubao-seedance-1-0-pro-250528') === 'ark', '视频供应商按模型ID路由（veo→google）');
  ok(prov.pickVideoProvider('veo-3.0-generate-001', { arkEnabled: true }).provider === 'google', 'Veo 模型路由到 Google');
  ok(prov.pickImageProvider('gpt-image-1', { arkEnabled: true }).enabled === false, '未配 OpenAI Key 时 GPT Image 不启用（安全）');
  ok(prov.imageModelOptions('doubao-seedream-4-0-250828').some((m) => m.id === 'gpt-image-1'), '图像模型清单含 GPT Image 选项');
  // 阿里通义万相（统一 DashScope API）：图/视频按 t2i/t2v/i2v 路由到 alibaba
  ok(prov.imageProviderOf('wanx2.1-t2i-turbo') === 'alibaba' && prov.imageProviderOf('qwen-image') === 'alibaba', '通义万相/Qwen-Image 路由到阿里');
  ok(prov.videoProviderOf('wanx2.1-i2v-turbo') === 'alibaba' && prov.videoProviderOf('wanx2.1-t2v-turbo') === 'alibaba', '通义万相视频（i2v/t2v）路由到阿里');
  ok(prov.pickVideoProvider('wanx2.1-i2v-turbo', { arkEnabled: true }).enabled === false, '未配 DashScope Key 时通义万相不启用（安全）');
  ok(prov.videoProviderOf('viduq1') === 'vidu' && prov.videoProviderOf('vidu2.0') === 'vidu' && prov.pickVideoProvider('viduq1', { arkEnabled: true }).enabled === false, 'Vidu 全能参考按 ID 路由，未配 Key 不启用（安全）');
  ok(prov.videoProviderOf('kling-v2-1') === 'kling' && prov.videoProviderOf('kling-v1-6') === 'kling' && prov.pickVideoProvider('kling-v2-5', { arkEnabled: true }).enabled === false, '可灵 Kling 按 ID 路由，未配 AK/SK 不启用（安全）');
  ok(prov.klingEnabled() === false, '未配 Kling AK/SK 时 klingEnabled 为 false');
  ok(prov.videoProviderOf('moxing/Kling-V3') === 'moxing' && prov.videoProviderOf('moxing/Sora-2-Pro') === 'moxing' && prov.pickVideoProvider('moxing/Kling-V3', { arkEnabled: true }).enabled === false, '墨行AI 聚合站按 moxing/ 前缀路由，未配 Key 不启用（安全）');
  ok(prov.moxingEnabled() === false && prov.maxVideoDuration('moxing/doubao-seedance-2-5') === 30, '墨行AI：未配 Key 为 false；时长按底层模型名判定（聚合 Seedance2.5→30s）');
  ok(prov.supportsMultiRef('viduq1') === true && prov.supportsMultiRef('kling-v2-1') === true && prov.supportsMultiRef('doubao-seedance-2-5') === false, '多主体参考能力：Vidu/可灵 支持，Seedance 不支持');
  const ark = await import(path.join(ROOT, 'server', 'lib', 'ark.js'));
  ok(ark.isQwenChat('qwen-max') === true && ark.isQwenChat('doubao-seed-1-6-250615') === false, '千问对话模型按 ID 识别');
  ok(ark.llmEnabled() === false, '无任何大模型 Key 时 llmEnabled 为 false（走本地）');
  // 电影级光影词库：场景按冷暖自适应（主控室=冷色调机房 → 冷调），分镜首帧含【光影】
  ok(/冷色调|清冷|漫反射/.test(dupSb.scenes[0].image_prompt || ''), '场景定义图含电影级光影词（冷暖自适应）');
  ok(/【光影】/.test(dupSb.shots[0].image_prompt || '') && /(丁达尔|暖调|冷色调|布光)/.test(dupSb.shots[0].image_prompt || ''), '分镜首帧注入光影词（丁达尔/暖冷调/布光）');
  // 穿越/换装剧：锁脸不锁衣——同一张脸可随年代换装（女子换上60年代蓝工装 / 民国学生装）
  const eraSb = normalizeStoryboard({
    title: '穿越', style: '写实电影质感',
    characters: [{ key: 'c1', name: '女子', role: '主角', gender: '女', desc: '25岁女性，乌黑长发，现代米色衬衫' }],
    scenes: [{ key: 's1', name: '办公室', desc: '60年代简陋办公室' }],
    shots: [
      { key: 'sh1', order: 1, scene: 's1', characters: ['c1'], shot_type: '近景', action: '女子换上60年代蓝工装，审视图纸' },
      { key: 'sh2', order: 2, scene: 's1', characters: ['c1'], shot_type: '中景', wardrobe: '民国蓝布学生装', action: '女子站在游行队伍中' }
    ]
  });
  ok(/脸型/.test(eraSb.characters[0].lock) && /(服装造型可随|仅换装不换脸)/.test(eraSb.characters[0].lock), '角色锁定改为锁脸（五官·脸型固定）+ 服装可换');
  ok(/【本镜造型】/.test(eraSb.shots[0].image_prompt) && /蓝工装/.test(eraSb.shots[0].image_prompt), '动作里自动识别换装 → 本镜造型覆盖（60年代蓝工装）');
  ok(/民国蓝布学生装/.test(eraSb.shots[1].image_prompt) && /(仍是同一人|脸型)/.test(eraSb.shots[1].image_prompt), '显式 wardrobe 字段 → 本镜造型（民国学生装）+ 脸不变');
  ok(/民国蓝布学生装/.test(eraSb.shots[1].video_prompt), '本镜造型也带进视频提示词');
  // AI 微表情提示词库：精确微表情名→细节面部描述；粗情绪词→大类通用线索；注入分镜首帧
  const mexp = await import(path.join(ROOT, 'server', 'lib', 'expressions.js'));
  ok(/脸颊泛绯红/.test(mexp.resolveExpression('心动羞涩笑')), '微表情精确名→细节面部描述（眉/眼/嘴/肌肉）');
  ok(mexp.resolveExpression('微笑').includes('微笑') && /嘴角上扬|眉眼/.test(mexp.resolveExpression('微笑')), '粗情绪词→大类通用面部线索');
  ok(mexp.listExpressions().length === 4 && mexp.listExpressions().every((c) => c.items.length === 10), '微表情库：喜/怒/哀/惊 4 大情绪 × 10');
  const emoSb = normalizeStoryboard({
    title: '表情', style: '写实电影质感',
    characters: [{ key: 'c1', name: '小满', role: '主角', gender: '女', desc: '20岁少女' }],
    scenes: [{ key: 's1', name: '房间', desc: '室内' }],
    shots: [{ key: 'sh1', order: 1, scene: 's1', characters: ['c1'], shot_type: '特写', emotion: '瞪眼质问', action: '小满质问对方' }]
  });
  ok(/【微表情】/.test(emoSb.shots[0].image_prompt) && /眼神锐利|瞪眼质问/.test(emoSb.shots[0].image_prompt), '分镜情绪解析为细节微表情注入首帧');
  ok(/【微表情】/.test(emoSb.shots[0].video_prompt), '微表情也带进视频提示词');
  // 分镜级时长上限放开到 30（存"意图时长"，出片时再按所选模型裁剪）
  const longShot = normalizeStoryboard({
    title: '长镜', style: '写实电影质感',
    characters: [{ key: 'c1', name: 'A', role: '主角', gender: '男', desc: '30岁男性' }],
    scenes: [{ key: 's1', name: 'S', desc: '室内' }],
    shots: [{ key: 'sh1', order: 1, scene: 's1', characters: ['c1'], shot_type: '全景', action: '长镜头慢推', duration: 25 }]
  });
  ok(longShot.shots[0].duration === 25, '分镜级时长不再被截到 12（存意图时长上限 30）');

  console.log('— 启动与基础 —');
  const boot = await until(async () => (await api('GET', '/api/bootstrap')).data, 10000);
  ok(boot.app.name === '灵境AI', 'bootstrap 返回应用信息');
  ok(/^ljk_/.test(boot.agent_token), '首次启动自动生成 Agent Token');
  ok(boot.ark.enabled === false, '未配 Key 时为本地引擎模式');
  ok(!!boot.ark.model_image_pro, 'bootstrap 暴露顶配图像模型（角色三视图/全场景图专用）');
  ok((boot.image_models || []).some((m) => m.id === 'gpt-image-1'), '创作框可选图像模型含 GPT Image（OpenAI）');
  ok((boot.image_models || []).some((m) => /wanx/i.test(m.id)), '创作框可选图像模型含 通义万相（阿里）');
  ok((boot.video_models || []).some((m) => /veo/i.test(m.id)), '创作框可选视频模型含 Veo 3（Google）');
  ok((boot.video_models || []).some((m) => /wanx|wan2/i.test(m.id)), '创作框可选视频模型含 通义万相（阿里）');
  ok((boot.video_models || []).some((m) => /vidu/i.test(m.id)), '创作框可选视频模型含 Vidu 全能参考');
  ok((boot.video_models || []).some((m) => /kling/i.test(m.id)), '创作框可选视频模型含 可灵 Kling');
  ok((boot.video_models || []).some((m) => /^moxing\//i.test(m.id)), '创作框可选视频模型含 墨行AI 聚合站（moxing/…）');
  ok(boot.providers && boot.providers.openai === false && boot.providers.google === false && boot.providers.alibaba === false && boot.providers.vidu === false && boot.providers.kling === false && boot.providers.moxing === false, '多供应商开通状态暴露（未配 Key 为 false）');
  ok(typeof boot.llm_enabled === 'boolean', 'bootstrap 暴露 llm_enabled（对话大模型可用性）');

  console.log('— 项目与剧本 —');
  const p = (await api('POST', '/api/projects', { title: '冒烟剧', genre: '悬疑反转', idea: '便利店午夜来客' })).data;
  ok(p.id && p.title === '冒烟剧', '创建项目');
  const gs = (await api('POST', '/api/ai/script', { project_id: p.id })).data;
  ok(gs.script.length > 300 && gs.by_llm === false, '本地引擎生成剧本');
  ok(gs.script.includes('第 1 场'), '剧本含场次结构');
  const upd = (await api('PATCH', `/api/projects/${p.id}`, { ratio: '9:16' })).data;
  ok(upd.ratio === '9:16', '更新项目画幅');

  console.log('— 解析与画布 —');
  const parsed = (await api('POST', '/api/ai/parse', { project_id: p.id })).data;
  ok(parsed.storyboard.characters.length >= 2, `解析出角色 ×${parsed.storyboard.characters.length}`);
  ok(parsed.storyboard.shots.length >= 4, `解析出分镜 ×${parsed.storyboard.shots.length}`);
  ok(!!parsed.canvas_id, '自动创建画布');
  const cv = (await api('GET', `/api/canvases/${parsed.canvas_id}`)).data;
  ok(cv.nodes.length >= parsed.storyboard.shots.length, `画布节点 ×${cv.nodes.length}`);
  ok(cv.edges.length >= parsed.storyboard.shots.length, `画布连线 ×${cv.edges.length}`);
  const shotNode = cv.nodes.find((n) => n.type === 'shot');
  const moved = (await api('PATCH', `/api/canvases/${cv.id}`, { nodes: cv.nodes.map((n) => n.id === shotNode.id ? { ...n, x: 999 } : n) }));
  ok(moved.ok, '保存画布');
  const cv2 = (await api('GET', `/api/canvases/${cv.id}`)).data;
  ok(cv2.nodes.find((n) => n.id === shotNode.id).x === 999, '画布数据持久化');

  console.log('— 涂鸦批注 —');
  const p0 = (await api('POST', '/api/projects', { title: '涂鸦测试' })).data;
  await api('POST', '/api/ai/script', { project_id: p0.id, num_scenes: 3 });
  const pr0 = (await api('POST', '/api/ai/parse', { project_id: p0.id })).data;
  const ddData = [{ id: 'd1', color: '#ff7a5c', width: 4.5, points: [[100, 100], [140, 90], [180, 130]] }];
  const ddSave = await api('PATCH', `/api/canvases/${pr0.canvas_id}`, { doodles: ddData });
  ok(ddSave.ok, '保存涂鸦笔迹');
  const cvDd = (await api('GET', `/api/canvases/${pr0.canvas_id}`)).data;
  ok(cvDd.doodles?.length === 1 && cvDd.doodles[0].points.length === 3, '涂鸦随画布持久化');
  await api('POST', '/api/ai/parse', { project_id: p0.id });
  const cvDd2 = (await api('GET', `/api/canvases/${pr0.canvas_id}`)).data;
  ok(cvDd2.doodles?.length === 1, '重新解析剧本后涂鸦保留');
  await api('DELETE', `/api/projects/${p0.id}`);

  console.log('— 图像与视频（本地引擎） —');
  const img = (await api('POST', '/api/ai/image', { prompt: '雨夜便利店空镜', name: '便利店', kind: 'scene', project_id: p.id, node_id: cv.nodes.find((n) => n.type === 'scene').id })).data;
  ok(img.url.startsWith('/uploads/') && img.provider === 'local', '本地出图并落盘');
  const imgFile = await fetch(BASE + img.url);
  ok(imgFile.status === 200 && (await imgFile.text()).includes('<svg'), '生成文件可访问');
  const vid = (await api('POST', '/api/ai/video', { prompt: '主角推门而入', duration: 4, project_id: p.id, node_id: shotNode.id, name: '镜头 1', order: 1 })).data;
  ok(vid.taskId && vid.status === 'running', '创建视频任务');
  const done = await until(async () => {
    const t = (await api('GET', `/api/ai/task/${vid.taskId}`)).data;
    return t.status === 'succeeded' ? t : null;
  });
  ok(done.result.url.startsWith('/uploads/'), '视频任务完成并产出文件');
  const cv3 = (await api('GET', `/api/canvases/${cv.id}`)).data;
  ok(cv3.nodes.find((n) => n.id === shotNode.id).data.video === done.result.url, '视频回写画布节点');

  console.log('— 爆款复刻 / 一镜到底 —');
  const rk = (await api('POST', '/api/ai/remake', { reference: '你绝对想不到，这家店凌晨三点还在排队！老板说出原因后所有人沉默了……', topic: '宠物殡葬师的温情日常', genre: '甜宠虐恋' })).data;
  ok(rk.project?.id && /第\s*1\s*场/.test(rk.script), '爆款复刻生成剧本并建项目');
  ok(rk.analysis?.hook && rk.analysis?.selling_points?.length >= 3, `结构解析（${rk.analysis?.hook}）`);
  await api('DELETE', `/api/projects/${rk.project.id}`);
  const upX = (await api('POST', '/api/upload', { name: '一镜测试帧', data: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' })).data;
  const v2 = (await api('POST', '/api/ai/video', { prompt: '镜头从首帧推到尾帧', image_url: upX.url, last_image_url: upX.url, duration: 3, name: '一镜到底' })).data;
  const v2t = (await api('GET', `/api/ai/task/${v2.taskId}`)).data;
  ok(v2t.params?.lastImageUrl === upX.url, '一镜到底尾帧参数入任务');
  ok((await api('GET', '/api/agent/v1/tools', undefined, boot.agent_token)).data.tools.some((t) => t.name === 'remake_viral'), 'Agent 开放 remake_viral 工具');

  console.log('— 角色表情集 —');
  const cvE = (await api('GET', `/api/canvases/${cv.id}`)).data;
  const charE = cvE.nodes.find((n) => n.type === 'character');
  const expr = (await api('POST', '/api/ai/expressions', { project_id: p.id, node_id: charE.id })).data;
  ok(expr.variants.length === 6 && expr.variants.every((v) => v.url.startsWith('/uploads/')), `生成 6 情绪定妆照`);
  const cvE2 = (await api('GET', `/api/canvases/${cv.id}`)).data;
  ok((cvE2.nodes.find((n) => n.id === charE.id)?.data.variants || []).length === 6, '表情集写入角色节点');
  ok((await api('GET', '/api/assets?tab=character')).data.some((a) => a.name.includes('·愤怒')), '表情入角色资产库');
  ok((await api('GET', '/api/agent/v1/tools', undefined, boot.agent_token)).data.tools.some((t) => t.name === 'generate_expressions'), 'Agent 开放 generate_expressions 工具');

  console.log('— 画面一致性 —');
  ok((await api('GET', `/api/projects/${p.id}`)).data.seed > 0, '项目自动持有一致性种子');
  const con1 = (await api('GET', `/api/projects/${p.id}/consistency`)).data;
  ok(con1.score <= 100 && Array.isArray(con1.issues) && con1.stats?.shots_framed, `体检报告（评分 ${con1.score}，问题 ${con1.issues.length} 项）`);
  // 给角色挂非 SVG 定妆照后，关联分镜首帧应记录 种子 + 参考图 + 锁定词
  const upC = (await api('POST', '/api/upload', { name: '定妆照', data: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' })).data;
  const cvCon = (await api('GET', `/api/canvases/${cv.id}`)).data;
  const conChar = cvCon.nodes.find((n) => n.type === 'character');
  const conShot = cvCon.nodes.find((n) => n.type === 'shot' && cvCon.edges.some((e) => e.from === conChar.id && e.to === n.id));
  await api('POST', '/api/agent/v1/tools/update_node', { project_id: p.id, node_id: conChar.id, patch: { image: upC.url } }, boot.agent_token);
  const conFrame = (await api('POST', '/api/ai/image', { prompt: '两人对峙特写', kind: 'frame', project_id: p.id, node_id: conShot.id })).data;
  const conTask = (await api('GET', `/api/ai/task/${conFrame.taskId}`)).data;
  ok(conTask.params?.seed > 0 && conTask.params?.ref_images >= 1, '首帧带种子 + 角色参考图');
  ok(/【角色】|五官发型服装固定|全片总控/.test(conTask.prompt || ''), '角色锁定档案注入首帧提示词');
  ok(/解剖|肢体残缺|人物完整|不被画框裁断|脚部在画面内|半身/.test(conTask.prompt || ''), '构图/解剖护栏注入首帧提示词（防上下身错位）');
  // 角色记忆 character_profile.json：锁定档案 + 总控 + 禁止项 + 已生成定妆照
  const prof = (await api('GET', `/api/projects/${p.id}/character-profile`)).data;
  ok(prof.schema === 'lingjing.character_profile/1' && Array.isArray(prof.characters) && prof.characters.length, `角色记忆导出（角色 ${prof.characters.length}）`);
  ok(prof.characters.every((c) => c.lock && c.name), '每个角色都带逐字锁定档案 lock');
  ok(prof.characters.every((c) => 'visual_signature' in c && 'default_wardrobe' in c), '角色记忆含视觉签名 + 默认造型（身份板字段）');
  ok(prof.characters.some((c) => c.ready && c.portrait === upC.url), '已生成定妆照写进角色记忆（portrait）');
  ok(/全片总控|铁律/.test(prof.master_control || '') && Array.isArray(prof.forbidden_rules) && prof.forbidden_rules.length >= 8, '角色记忆含总控提示词 + 全部禁止项');
  ok(/画风铁律|切换画风/.test(prof.master_control || ''), '画风锚定：总控含"全片只用一种画风"铁律（防日漫↔2D跳风）');
  ok(prof.forbidden_rules.some((r) => /三只手|多指|多出的手/.test(r)) && prof.forbidden_rules.some((r) => /身高|头身比/.test(r)), '禁止项含"多手/三只手"与"身高头身比突变"');
  ok(prof.characters.every((c) => /身高体型|体型比例/.test(c.lock)), '角色锁定档案含身高体型固定（防一米五变一米七）');
  const setChain = (await api('GET', '/api/settings')).data.video_chain;
  ok(setChain === true, '视频接龙默认开启（上段尾帧→下段首帧）');
  const agentTools = (await api('GET', '/api/agent/v1/tools', undefined, boot.agent_token)).data.tools;
  ok(agentTools.some((t) => t.name === 'check_consistency'), 'Agent 开放 check_consistency 工具');
  ok(agentTools.some((t) => t.name === 'get_character_profile'), 'Agent 开放 get_character_profile 工具（角色记忆）');
  ok(agentTools.some((t) => t.name === 'list_entities') && agentTools.some((t) => t.name === 'annotate_entities'), 'Agent 开放 list_entities/annotate_entities 工具');
  ok(agentTools.some((t) => t.name === 'omni_reference_script') && agentTools.some((t) => t.name === 'omni_reference_video'), 'Agent 开放 omni_reference_script/video 工具（全能参考）');
  ok(agentTools.some((t) => t.name === 'storyboard_sheet'), 'Agent 开放 storyboard_sheet 工具（故事板图）');
  ok(agentTools.some((t) => t.name === 'list_expressions'), 'Agent 开放 list_expressions 工具（微表情库）');
  const exps = (await api('GET', '/api/expressions')).data;
  ok(exps.categories?.length === 4 && exps.categories.every((c) => c.items.length === 10), 'GET /api/expressions 返回 4×10 微表情库');

  console.log('— LLM Wiki 自维护知识库 —');
  // 解析后自动摄入：项目角色/场景/总览建页（domain=video, namespace=项目id）
  const wpages = (await api('GET', `/api/wiki?domain=video&namespace=${p.id}`)).data.pages;
  ok(Array.isArray(wpages) && wpages.length >= 2 && wpages.some((x) => /^角色·/.test(x.title)) && wpages.some((x) => /^作品总览·/.test(x.title)), '解析后自动摄入知识库：角色/场景/总览建页');
  const charPage = wpages.find((x) => /^角色·/.test(x.title));
  const wq = (await api('POST', '/api/wiki/query', { query: charPage.title.replace('角色·', ''), domain: 'video', namespace: p.id, synthesize: false })).data;
  ok(wq.hits >= 1 && wq.pages.some((x) => x.id === charPage.id), 'wiki 查询命中角色页');
  // 摄入 global 页并查到
  await api('POST', '/api/wiki/ingest', { title: '品牌规范·LingMirror', content: '暗黑科技风、苹果质感、中英双语国际化', domain: 'global', source: 'test' });
  const wq2 = (await api('POST', '/api/wiki/query', { query: '品牌 暗黑科技 苹果', synthesize: false })).data;
  ok(wq2.pages.some((x) => x.title === '品牌规范·LingMirror'), 'wiki 摄入页可被查询命中');
  // 域分区：music 域页不串入 video（音乐/视频/Agent 共库不串味）
  await api('POST', '/api/wiki/ingest', { title: '音乐风格·赛博', content: '合成器、未来感、电子节拍', domain: 'music', source: 'test' });
  const wMusic = (await api('POST', '/api/wiki/query', { query: '赛博 合成器', domain: 'music', synthesize: false })).data;
  const wVideo = (await api('POST', '/api/wiki/query', { query: '赛博 合成器', domain: 'video', synthesize: false })).data;
  ok(wMusic.hits >= 1 && wVideo.pages.every((x) => x.title !== '音乐风格·赛博'), 'wiki 域分区：music 页不串入 video（视频/音乐/Agent 同库不串味）');
  const waudit = (await api('GET', '/api/wiki/audit')).data;
  ok(typeof waudit.total === 'number' && waudit.domains.includes('music') && waudit.domains.includes('video'), 'wiki 审计返回总数与域分布');
  const wtools = (await api('GET', '/api/agent/v1/tools', undefined, boot.agent_token)).data.tools;
  ok(['wiki_query', 'wiki_ingest', 'wiki_audit', 'wiki_page'].every((n) => wtools.some((t) => t.name === n)), 'Agent/MCP 开放 wiki_query/ingest/audit/page（外部音乐站经 MCP 共享同库）');
  // 外部应用（音乐站）经 knowledge-client.js → HTTP MCP 读写同库（ingest→query 闭环）
  const { knowledge } = await import(path.join(ROOT, 'integrations', 'knowledge-client.js'));
  const kb = knowledge({ baseUrl: BASE, token: boot.agent_token, domain: 'music' });
  await kb.ingest({ title: '客户端·音乐测试页', content: '通过 MCP 客户端写入的音乐知识：合成器、未来感、电子节拍' });
  const kbq = await kb.query('客户端 音乐测试');
  ok(kbq.pages?.some((x) => x.title === '客户端·音乐测试页'), '音乐站客户端经 MCP ingest→query 成功（与视频站共享同库）');
  let kbAuthErr = '';
  try { await knowledge({ baseUrl: BASE, token: 'wrong-token', domain: 'music' }).query('x'); } catch (e) { kbAuthErr = e.message; }
  ok(/鉴权失败|Token/.test(kbAuthErr), '客户端 Token 不对时鉴权失败（跨站安全）');
  // HTTP 版 MCP 端点（设置页「MCP 测试窗口」走的同一条路）：initialize / tools/list / ping / tools/call
  const mcpInit = (await api('POST', '/api/agent/v1/mcp', { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05' } }, boot.agent_token));
  ok(mcpInit.result?.serverInfo?.name === 'lingjing-studio' && !!mcpInit.result?.protocolVersion, 'HTTP MCP initialize 返回 serverInfo/protocolVersion');
  const mcpList = (await api('POST', '/api/agent/v1/mcp', { jsonrpc: '2.0', id: 2, method: 'tools/list' }, boot.agent_token));
  ok(Array.isArray(mcpList.result?.tools) && mcpList.result.tools.every((t) => t.name && t.inputSchema), 'HTTP MCP tools/list 返回带 inputSchema 的工具');
  const mcpPing = (await api('POST', '/api/agent/v1/mcp', { jsonrpc: '2.0', id: 3, method: 'ping' }, boot.agent_token));
  ok(mcpPing.result && Object.keys(mcpPing.result).length === 0 && !mcpPing.error, 'HTTP MCP ping 返回空结果');
  const mcpCall = (await api('POST', '/api/agent/v1/mcp', { jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'studio_overview', arguments: {} } }, boot.agent_token));
  ok(typeof mcpCall.result?.content?.[0]?.text === 'string' && !mcpCall.result?.isError, 'HTTP MCP tools/call(studio_overview) 返回 content 文本');
  const mcpBad = (await api('POST', '/api/agent/v1/mcp', { jsonrpc: '2.0', id: 5, method: 'no_such_method' }, boot.agent_token));
  ok(mcpBad.error?.code === -32601, 'HTTP MCP 未知方法返回 JSON-RPC -32601');

  console.log('— 角色预选标注 / Agent 进化 —');
  const pe = (await api('POST', '/api/projects', { title: '标注剧', genre: '悬疑反转', idea: '实验室停电夜' })).data;
  await api('POST', '/api/ai/script', { project_id: pe.id });
  await api('POST', '/api/ai/parse', { project_id: pe.id });
  const ents0 = (await api('GET', `/api/projects/${pe.id}/entities`)).data;
  ok(Array.isArray(ents0.entities) && ents0.entities.length && ents0.brain, `实体清单（${ents0.counts.character} 角 / ${ents0.counts.scene} 景 / ${ents0.counts.prop} 道）`);
  const victim = ents0.entities.find((e) => e.type === 'character');
  ok(!!victim, '存在可校验的角色');
  const ann = (await api('POST', `/api/projects/${pe.id}/annotate`, { moves: [{ name: victim.name, to: 'prop' }] })).data;
  ok(ann.applied.some((m) => m.name === victim.name && m.to === 'prop'), '人工校正：角色→道具已归位');
  ok(ann.brain.xp > ents0.brain.xp && ann.brain.learned >= 1, 'Agent 训练后涨经验并记住分类');
  await api('POST', '/api/ai/parse', { project_id: pe.id });   // 重解析验证进化是否持久
  const ents1 = (await api('GET', `/api/projects/${pe.id}/entities`)).data;
  ok(ents1.entities.find((e) => e.name === victim.name)?.type === 'prop', '进化持久化：重新解析仍把它判成道具');
  const praise = (await api('POST', `/api/projects/${pe.id}/annotate`, { confirm: true })).data;
  ok(praise.praised && praise.brain.streak >= 1 && praise.brain.xp > ann.brain.xp, '夸赞奖励：连击 +1、经验上涨');
  await api('POST', `/api/projects/${pe.id}/annotate`, { moves: [{ name: victim.name, to: 'character' }] });   // 复位全局标签，避免影响其它用例
  await api('DELETE', `/api/projects/${pe.id}`);

  // 画风重锚定：解析后改画风 → 全片总控随之更新（杜绝前后画风不连贯）
  const pr = (await api('POST', '/api/projects', { title: '锚风剧', genre: '悬疑反转', idea: '地铁末班车' })).data;
  await api('POST', '/api/ai/script', { project_id: pr.id });
  await api('POST', '/api/ai/parse', { project_id: pr.id });
  const profA = (await api('GET', `/api/projects/${pr.id}/character-profile`)).data;
  await api('PATCH', `/api/projects/${pr.id}`, { style: '美式复古好莱坞' });
  const profB = (await api('GET', `/api/projects/${pr.id}/character-profile`)).data;
  ok(profB.master_control !== profA.master_control && (profB.project.style || '').length > 0, '改画风后全片重锚定（总控随之更新为新画风）');
  await api('DELETE', `/api/projects/${pr.id}`);
  // 情绪联动 + 跨镜参考链：同场景相邻两镜，前镜挂 PNG 首帧、后镜设情绪
  const pair = (() => {
    const shots = cvCon.nodes.filter((n) => n.type === 'shot').sort((a, b) => a.data.order - b.data.order);
    for (let i = 1; i < shots.length; i++) {
      if (shots[i].data.scene === shots[i - 1].data.scene && shots[i].data.order === shots[i - 1].data.order + 1) return [shots[i - 1], shots[i]];
    }
    return null;
  })();
  ok(!!pair, '存在同场景相邻分镜对');
  await api('POST', '/api/agent/v1/tools/update_node', { project_id: p.id, node_id: pair[0].id, patch: { image: upC.url } }, boot.agent_token);
  await api('POST', '/api/agent/v1/tools/update_node', { project_id: p.id, node_id: pair[1].id, patch: { emotion: '愤怒' } }, boot.agent_token);
  const chainFrame = (await api('POST', '/api/ai/image', { prompt: '冲突升级', kind: 'frame', project_id: p.id, node_id: pair[1].id })).data;
  const chainTask = (await api('GET', `/api/ai/task/${chainFrame.taskId}`)).data;
  ok(chainTask.params?.chain_ref === true, '跨镜参考链：上一镜首帧已入参考');
  ok(chainTask.params?.emotion === '愤怒' && /愤怒/.test(chainTask.prompt || ''), '分镜情绪注入提示词');

  console.log('— 配音（TTS） —');
  const dub = await api('POST', '/api/ai/dub', { project_id: p.id });
  ok(dub.status === 400 && /语音|TTS|AppID/i.test(dub.error || ''), '未配置 TTS 时给出可执行引导');
  await api('PATCH', '/api/settings', { tts_appid: 'test-appid', tts_voice: 'BV002_streaming' });
  const setTts = (await api('GET', '/api/settings')).data;
  ok(setTts.tts_appid === 'test-appid' && setTts.tts_voice === 'BV002_streaming' && setTts.tts_enabled === false, 'TTS 设置保存（无 Token 仍为未启用）');
  ok((await api('GET', '/api/agent/v1/tools', undefined, boot.agent_token)).data.tools.some((t) => t.name === 'generate_dubbing'), 'Agent 开放 generate_dubbing 工具');

  console.log('— 成片导出 —');
  const exp = await api('POST', `/api/projects/${p.id}/export`, {});
  ok(exp.status === 400 && /ffmpeg|MP4/.test(exp.error || ''), '导出端点给出可执行的引导（无 ffmpeg / 缺 MP4 时不误报成功）');
  const expNoSb = await api('POST', `/api/projects/not-exist/export`, {});
  ok(expNoSb.status === 404, '导出不存在项目报 404');

  console.log('— 资产库 —');
  const assets = (await api('GET', '/api/assets')).data;
  ok(assets.length >= 2, `资产自动入库 ×${assets.length}`);
  const up = (await api('POST', '/api/upload', { name: '上传图', data: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' })).data;
  ok(up.url.startsWith('/uploads/'), '上传 dataURL 资产');
  const ren = (await api('PATCH', `/api/assets/${up.id}`, { name: '重命名图' })).data;
  ok(ren.name === '重命名图', '重命名资产');

  console.log('— 资产分页 —');
  const pg = (await api('GET', '/api/assets?paged=1&limit=2')).data;
  ok(typeof pg.total === 'number' && pg.items.length <= 2, `分页返回（total=${pg.total}）`);
  const pg2 = (await api('GET', '/api/assets?paged=1&limit=2&offset=2')).data;
  ok(pg2.offset === 2 && (pg.total <= 2 || pg2.items[0]?.id !== pg.items[0]?.id), '偏移翻页生效');
  ok(Array.isArray((await api('GET', '/api/assets')).data), '旧数组形态保持兼容');

  console.log('— Agent API（Token 鉴权） —');
  const noAuth = await api('GET', '/api/agent/v1/ping');
  ok(noAuth.status === 401, '无 Token 拒绝（401）');
  const token = boot.agent_token;
  const ping = await api('GET', '/api/agent/v1/ping', undefined, token);
  ok(ping.data?.pong === true, 'Token 通过 ping');
  const tools = (await api('GET', '/api/agent/v1/tools', undefined, token)).data;
  ok(tools.tools.length >= 14, `开放工具 ×${tools.tools.length}`);
  const openapi = await (await fetch(BASE + '/api/agent/v1/openapi.json')).json();
  ok(openapi.openapi === '3.1.0' && Object.keys(openapi.paths).length >= 16, 'OpenAPI 描述完整');
  const ov = (await api('POST', '/api/agent/v1/tools/studio_overview', {}, token)).data;
  ok(ov.result.projects >= 1, '工具调用 studio_overview');
  const batch = (await api('POST', '/api/agent/v1/tools/generate_storyboard_media', { project_id: p.id, target: 'images', limit: 3 }, token)).data;
  ok(batch.result.generated >= 1, `批量出图工具 ×${batch.result.generated}`);
  const badTool = await api('POST', '/api/agent/v1/tools/not_exist', {}, token);
  ok(badTool.status === 400, '未知工具报错');

  console.log('— 内置 Agent（本地意图） —');
  const chat1 = (await api('POST', '/api/ai/agent', { messages: [{ role: 'user', content: '创建一个废土科幻项目并写剧本' }] })).data;
  ok(chat1.steps.some((s) => s.tool === 'create_project') && chat1.steps.some((s) => s.tool === 'generate_script'), 'Agent 连续调用 创建+写剧本');
  const chat2 = (await api('POST', '/api/ai/agent', { messages: [{ role: 'user', content: '解析分镜' }] })).data;
  ok(chat2.steps.some((s) => s.tool === 'parse_script'), 'Agent 解析分镜');
  const logs = (await api('GET', '/api/agent/v1/logs', undefined, token)).data;
  ok(logs.logs.length >= 4, `Agent 调用日志 ×${logs.logs.length}`);

  console.log('— 风格库 —');
  const stylesData = (await api('GET', '/api/styles')).data;
  ok(stylesData.styles.length >= 24 && stylesData.cats.length === 4, `风格库 ×${stylesData.styles.length}（4 类）`);
  const updP = (await api('POST', '/api/agent/v1/tools/update_project', { project_id: p.id, style: '美式复古好莱坞' }, token)).data;
  ok(updP.result.style === '美式复古好莱坞', 'update_project 设置风格');
  const styledImg = (await api('POST', '/api/ai/image', { prompt: '街角夜景空镜', name: '风格测试', kind: 'scene', project_id: p.id })).data;
  const styledTask = (await api('GET', `/api/ai/task/${styledImg.taskId}`)).data;
  ok((await api('GET', '/api/assets')).data.some((a) => a.name === '风格测试' && a.prompt.includes('好莱坞')), '风格自动注入生图提示词');
  const ls = (await api('POST', '/api/agent/v1/tools/list_styles', { cat: 'd3' }, token)).data;
  ok(ls.result.styles.length >= 5 && ls.result.styles.every((s) => s.cat === 'd3'), 'list_styles 按分类过滤');

  console.log('— 分集（多集短剧） —');
  const p2 = (await api('POST', '/api/projects', { title: '分集剧', genre: '都市逆袭' })).data;
  const ms = (await api('POST', '/api/ai/script', { project_id: p2.id, num_episodes: 2, num_scenes: 3 })).data;
  ok(/第\s*2\s*集/.test(ms.script), '生成 2 集剧本（含分集标记）');
  const mp = (await api('POST', '/api/ai/parse', { project_id: p2.id })).data;
  ok(mp.storyboard.episodes.length === 2, `解析出 ${mp.storyboard.episodes.length} 集`);
  ok(mp.storyboard.shots.some((s) => s.episode === 'e2'), '分镜归属到第 2 集');
  const sceneNames = mp.storyboard.scenes.map((s) => s.name);
  ok(new Set(sceneNames).size === sceneNames.length, '跨集场景按名去重');
  const epAdd = (await api('POST', '/api/agent/v1/tools/add_episode', { project_id: p2.id, idea: '幕后大boss现身' }, token)).data;
  ok(epAdd.result.episode_order === 3 && epAdd.result.episodes.length === 3, 'add_episode 续写第 3 集并重解析');
  ok(epAdd.result.new_episode_shots >= 2, `第 3 集新增分镜 ×${epAdd.result.new_episode_shots}`);
  const epImgs = (await api('POST', '/api/agent/v1/tools/generate_storyboard_media', { project_id: p2.id, target: 'images', episode: 'e2', limit: 20 }, token)).data;
  const cvEp = (await api('GET', `/api/canvases/${(await api('GET', `/api/projects/${p2.id}`)).data.canvas_id}`)).data;
  const otherEpShotWithImage = cvEp.nodes.filter((n) => n.type === 'shot' && (n.data.episode || 'e1') !== 'e2' && n.data.image).length;
  ok(epImgs.result.generated >= 1 && otherEpShotWithImage === 0, '按集批量出图只处理该集分镜');

  console.log('— 创作框：按次模型/分辨率 + 主体一致性 —');
  ok(boot.video_models?.length >= 3, `可选视频模型 ×${boot.video_models?.length}`);
  await api('PATCH', '/api/settings', { model_video_options: 'Seedance 2.0|seedance-2-0-test\nSeedance 1.0 Pro|doubao-seedance-1-0-pro-250528' });
  const boot2 = (await api('GET', '/api/bootstrap')).data;
  ok(boot2.video_models.some((m) => m.id === 'seedance-2-0-test'), '设置页维护模型列表立即生效');
  const qv = (await api('POST', '/api/ai/video', { prompt: '一只机械猫撑伞走过雨夜街头', duration: 3, ratio: '9:16', model: 'seedance-2-0-test', resolution: '720p', name: '快速短片' })).data;
  const qvt = await until(async () => {
    const t = (await api('GET', `/api/ai/task/${qv.taskId}`)).data;
    return t.status === 'succeeded' ? t : null;
  });
  ok(qvt.result.url.startsWith('/uploads/'), '无项目快速短片生成');
  const qvTask = (await api('GET', `/api/ai/task/${qv.taskId}`)).data;
  ok(qvTask.params?.model === 'seedance-2-0-test' && qvTask.params?.resolution === '720p', '按次模型/分辨率已记录到任务');
  // 主体一致性：给角色节点挂非 SVG 定妆图后，关联分镜的首帧自动带参考图
  const cvX = (await api('GET', `/api/canvases/${(await api('GET', `/api/projects/${p.id}`)).data.canvas_id}`)).data;
  const charNode = cvX.nodes.find((n) => n.type === 'character');
  const linkedShot = cvX.nodes.find((n) => n.type === 'shot' && cvX.edges.some((e) => e.from === charNode.id && e.to === n.id));
  await api('POST', '/api/agent/v1/tools/update_node', { project_id: p.id, node_id: charNode.id, patch: { image: up.url } }, token);
  const frame = (await api('POST', '/api/ai/image', { prompt: '主角站在门口回头', kind: 'frame', project_id: p.id, node_id: linkedShot.id })).data;
  const frameTask = (await api('GET', `/api/ai/task/${frame.taskId}`)).data;
  ok(frame.url && frameTask.params?.ref_images >= 1, `首帧自动引用关联角色定妆图 ×${frameTask.params?.ref_images}`);
  // 角色三视图/全场景图走顶配模型路由 + 角色用宽幅（横排正/侧/背）
  const charImg = (await api('POST', '/api/ai/image', { prompt: '主角', kind: 'character', project_id: p.id, name: '三视图测试' })).data;
  const charTask = (await api('GET', `/api/ai/task/${charImg.taskId}`)).data;
  ok(charTask.params?.pro === true && charTask.params?.ratio === '16:9', '角色图走顶配模型路由 + 三视图宽幅(16:9)');
  const sceneImg = (await api('POST', '/api/ai/image', { prompt: '废墟街道', kind: 'scene', project_id: p.id, name: '全场景测试' })).data;
  ok((await api('GET', `/api/ai/task/${sceneImg.taskId}`)).data.params?.pro === true, '全场景图走顶配模型路由');
  // 全能参考：分镜拼成带编号图片引用的多镜头剧本 + 编号→参考图清单
  const omni = (await api('GET', `/api/projects/${p.id}/omni-reference`)).data;
  ok(/镜头1/.test(omni.prompt) && /图片1/.test(omni.prompt) && Array.isArray(omni.references) && omni.references.length >= 1, '全能参考：分镜拼成带编号图片引用的多镜头剧本');
  ok(omni.references[0].n === 1 && omni.references.some((r) => r.type === '场景') && /摄影|景深/.test(omni.prompt), '全能参考：编号清单（角色优先+场景）+ 每镜含摄影机参数');
  // 全能参考一键出片：模型跟随所选视频模型；Vidu/可灵=真·多主体参考，其余退化首图并标注
  const omniVidu = (await api('POST', `/api/projects/${p.id}/omni-video`, { model: 'viduq1' })).data;
  ok(omniVidu.multi_ref === true && !omniVidu.note, '选 Vidu 时全能参考为真·多主体参考');
  const omniSd = (await api('POST', `/api/projects/${p.id}/omni-video`, { model: 'doubao-seedance-2-5' })).data;
  ok(omniSd.multi_ref === false && /多主体参考/.test(omniSd.note || ''), '选非多图模型时退化为首图参考并标注');
  const omniVid = (await api('POST', `/api/projects/${p.id}/omni-video`, {})).data;
  ok(omniVid.taskId && omniVid.used_images >= 1, '全能参考一键出片：创建任务并带入多张参考图');
  const omniDone = await until(async () => {
    const t = (await api('GET', `/api/ai/task/${omniVid.taskId}`)).data;
    return ['succeeded', 'failed'].includes(t.status) ? t : null;
  });
  ok(omniDone.provider === 'local' && omniDone.status === 'succeeded', '未配 Vidu Key 时全能参考出片回退本地占位');
  // 故事板图：整段分镜画成 N 宫格故事板（限定景别与运动）
  const sheetPrev = (await api('GET', `/api/projects/${p.id}/storyboard-sheet?max=9`)).data;
  ok(/宫格/.test(sheetPrev.prompt) && /第1格\[/.test(sheetPrev.prompt) && sheetPrev.count === 9 && sheetPrev.cols === 3, '故事板提示词：N 宫格 + 每格镜号/景别/运镜');
  const sheetGen = (await api('POST', `/api/projects/${p.id}/storyboard-sheet`, { max: 12 })).data;
  ok(sheetGen.url && sheetGen.count === 12 && sheetGen.cols === 4 && sheetGen.rows === 3, '生成故事板图（12 宫格 4×3，已入资产库）');
  // 多供应商安全回退：未配对应 Key 时选 GPT Image / Veo 3 → 回退本地占位，不报错也不假装成功
  const gptImg = (await api('POST', '/api/ai/image', { prompt: '测试', kind: 'scene', project_id: p.id, model: 'gpt-image-1' })).data;
  const gptTask = (await api('GET', `/api/ai/task/${gptImg.taskId}`)).data;
  ok(gptTask.provider === 'local' && /\.svg$/i.test(gptImg.url), '未配 OpenAI Key 选 GPT Image → 安全回退本地占位');
  const veoVid = (await api('POST', '/api/ai/video', { prompt: '测试', model: 'veo-3.0-generate-001', ratio: '16:9', duration: 3 })).data;
  const veoDone = await until(async () => {
    const t = (await api('GET', `/api/ai/task/${veoVid.taskId}`)).data;
    return ['succeeded', 'failed'].includes(t.status) ? t : null;
  });
  ok(veoDone.provider === 'local' && veoDone.status === 'succeeded', '未配 Google Key 选 Veo 3 → 安全回退本地占位');
  const wanImg = (await api('POST', '/api/ai/image', { prompt: '测试', kind: 'scene', project_id: p.id, model: 'wanx2.1-t2i-turbo' })).data;
  ok((await api('GET', `/api/ai/task/${wanImg.taskId}`)).data.provider === 'local' && /\.svg$/i.test(wanImg.url), '未配 DashScope Key 选通义万相图 → 安全回退本地占位');
  const wanVid = (await api('POST', '/api/ai/video', { prompt: '测试', model: 'wanx2.1-i2v-turbo', ratio: '16:9', duration: 3 })).data;
  const wanDone = await until(async () => {
    const t = (await api('GET', `/api/ai/task/${wanVid.taskId}`)).data;
    return ['succeeded', 'failed'].includes(t.status) ? t : null;
  });
  ok(wanDone.provider === 'local' && wanDone.status === 'succeeded', '未配 DashScope Key 选通义万相视频 → 安全回退本地占位');
  const klingFb = (await api('POST', '/api/ai/video', { prompt: '测试', model: 'kling-v2-1', ratio: '16:9', duration: 5 })).data;
  const klingDone = await until(async () => { const t = (await api('GET', `/api/ai/task/${klingFb.taskId}`)).data; return ['succeeded', 'failed'].includes(t.status) ? t : null; });
  ok(klingDone.provider === 'local' && klingDone.status === 'succeeded', '未配 Kling AK/SK 选可灵 → 安全回退本地占位');
  const moxFb = (await api('POST', '/api/ai/video', { prompt: '测试', model: 'moxing/Kling-V3', ratio: '16:9', duration: 5 })).data;
  const moxDone = await until(async () => { const t = (await api('GET', `/api/ai/task/${moxFb.taskId}`)).data; return ['succeeded', 'failed'].includes(t.status) ? t : null; });
  ok(moxDone.provider === 'local' && moxDone.status === 'succeeded', '未配 墨行AI Key 选聚合站模型 → 安全回退本地占位');
  // 时长按模型上限：Seedance 2.5→30s、2.0→15s，其余默认 12s
  const d25 = (await api('GET', `/api/ai/task/${(await api('POST', '/api/ai/video', { prompt: '长片', model: 'doubao-seedance-2-5', duration: 30 })).data.taskId}`)).data;
  const d20 = (await api('GET', `/api/ai/task/${(await api('POST', '/api/ai/video', { prompt: '长片', model: 'doubao-seedance-2-0', duration: 30 })).data.taskId}`)).data;
  const d10 = (await api('GET', `/api/ai/task/${(await api('POST', '/api/ai/video', { prompt: '默认', duration: 30 })).data.taskId}`)).data;
  ok(d25.params.duration === 30 && d20.params.duration === 15 && d10.params.duration === 12, '视频时长按模型上限裁剪（2.5→30s / 2.0→15s / 默认→12s）');

  console.log('— MCP over HTTP（远程助理通道） —');
  const mh = async (msg) => {
    const res = await fetch(BASE + '/api/agent/v1/mcp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(msg)
    });
    return { status: res.status, body: res.status === 202 ? null : await res.json() };
  };
  const hInit = await mh({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18' } });
  ok(hInit.body?.result?.serverInfo?.name === 'lingjing-studio', 'HTTP MCP initialize');
  const hNote = await mh({ jsonrpc: '2.0', method: 'notifications/initialized' });
  ok(hNote.status === 202, 'HTTP MCP 通知返回 202');
  const hTools = await mh({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
  ok(hTools.body?.result?.tools?.length >= 16, `HTTP MCP tools/list ×${hTools.body?.result?.tools?.length}`);
  const hCall = await mh({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'list_projects', arguments: {} } });
  ok(hCall.body?.result?.content?.[0]?.text?.includes('冒烟剧'), 'HTTP MCP tools/call');
  const hNoAuth = await fetch(BASE + '/api/agent/v1/mcp', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', id: 9, method: 'ping' }) });
  ok(hNoAuth.status === 401, 'HTTP MCP 无 Token 拒绝');

  console.log('— Agent v2（意图分析 + 规划 + 调度） —');
  const ag1 = (await api('POST', '/api/ai/agent', { messages: [{ role: 'user', content: '做一部末日生存的电影，写剧本并解析分镜' }] })).data;
  ok(ag1.thinking && ag1.plan?.length >= 2, `输出思考与规划（${ag1.plan?.join('→')}）`);
  ok(ag1.steps.some((s) => s.tool === 'create_project') && ag1.steps.some((s) => s.tool === 'generate_script') && ag1.steps.some((s) => s.tool === 'parse_script'), '复合指令一轮内多步调度');
  const ag2 = (await api('POST', '/api/ai/agent', { messages: [{ role: 'user', content: '现在进度怎么样' }] })).data;
  ok(ag2.steps.some((s) => s.tool === 'studio_overview'), '查询意图路由到总览');
  await api('PATCH', '/api/settings', { agent_autorun: false });
  const ag3 = (await api('POST', '/api/ai/agent', { messages: [{ role: 'user', content: '创建一个甜宠短剧并写剧本' }] })).data;
  ok(ag3.intent === 'plan' && ag3.steps.length === 0, '关闭自动执行时只规划不动手');
  await api('PATCH', '/api/settings', { agent_autorun: true });
  const setA = (await api('GET', '/api/settings')).data;
  ok(setA.agent && typeof setA.agent.temperature === 'number' && typeof setA.agent.max_steps === 'number', 'Agent 参数可读写');

  console.log('— 全流程工作流 —');
  const p9 = (await api('POST', '/api/projects', { title: '工作流剧', genre: '都市逆袭', idea: '保安逆袭成集团总裁' })).data;
  const wf = (await api('POST', '/api/workflows', { project_id: p9.id, video_model: 'doubao-seedance-2-5' })).data;
  ok(wf.id && wf.status === 'running' && wf.steps.length === 9, '工作流启动（9 步含表情+AIQC）');
  ok((await api('GET', `/api/workflows/${wf.id}`)).data.video_model === 'doubao-seedance-2-5', '工作流记住所选视频模型（批量出片用）');
  const wfDone = await until(async () => {
    const w = (await api('GET', `/api/workflows/${wf.id}`)).data;
    return w.status !== 'running' ? w : null;
  }, 90_000);
  ok(wfDone.status === 'succeeded', `工作流完成（${wfDone.status}）`);
  const stepMap = Object.fromEntries(wfDone.steps.map((s) => [s.name, s]));
  ok(stepMap.script.status === 'done' && stepMap.parse.status === 'done' && stepMap.images.status === 'done', '剧本/解析/出图步骤完成');
  ok(stepMap.videos.status === 'done' && /(完成|接龙) \d+\/\d+/.test(stepMap.videos.detail), `视频步骤：${stepMap.videos.detail}`);
  ok(stepMap.dub.status === 'skipped' && stepMap.export.status === 'skipped', 'TTS/ffmpeg 未配置步骤自动跳过');
  ok(stepMap.qc && stepMap.qc.status === 'done' && /质检/.test(stepMap.qc.detail), `AIQC 质检步骤执行（${stepMap.qc.detail}）`);
  const qcRep = (await api('GET', `/api/projects/${p9.id}/qc`)).data;
  ok(qcRep.summary && qcRep.records.length >= 1, `QC 记录生成（${qcRep.records.length} 条，均分 ${qcRep.summary.avg_score}）`);
  const p9done = (await api('GET', `/api/projects/${p9.id}`)).data;
  const cv9 = (await api('GET', `/api/canvases/${p9done.canvas_id}`)).data;
  ok(cv9.nodes.filter((n) => n.type === 'shot').every((n) => n.data.video), '全部分镜已出片');
  ok((await api('GET', '/api/agent/v1/tools', undefined, boot.agent_token)).data.tools.filter((t) => ['run_workflow', 'get_workflow'].includes(t.name)).length === 2, 'Agent 开放工作流工具');
  // 取消工作流应同步结束该项目仍在进行的视频任务（修"停不下来"）
  const p10 = (await api('POST', '/api/projects', { title: '取消测试' })).data;
  await api('POST', '/api/ai/script', { project_id: p10.id, num_scenes: 3 });
  await api('POST', '/api/ai/parse', { project_id: p10.id });
  const wf2 = (await api('POST', '/api/workflows', { project_id: p10.id })).data;
  await api('POST', `/api/workflows/${wf2.id}/cancel`);
  const wf2s = (await api('GET', `/api/workflows/${wf2.id}`)).data;
  ok(wf2s.cancel === 1 || wf2s.status === 'cancelled', '工作流可取消');
  ok(!(await api('GET', '/api/ai/tasks?kind=video&status=active')).data.some((t) => t.project_id === p10.id), '取消后该项目无残留进行中视频任务');
  await api('DELETE', `/api/projects/${p10.id}`);
  await api('DELETE', `/api/projects/${p9.id}`);

  console.log('— 回收站 / 任务重试 —');
  const pT = (await api('POST', '/api/projects', { title: '回收站测试' })).data;
  await api('DELETE', `/api/projects/${pT.id}`);
  ok(!(await api('GET', '/api/projects')).data.some((x) => x.id === pT.id), '软删除后不在项目列表');
  ok((await api('GET', '/api/projects/trash')).data.some((x) => x.id === pT.id), '出现在回收站');
  const agentList = (await api('POST', '/api/agent/v1/tools/list_projects', {}, token)).data.result;
  ok(!agentList.some((x) => x.id === pT.id), 'Agent list_projects 不含回收站项目');
  await api('POST', `/api/projects/${pT.id}/restore`);
  ok((await api('GET', '/api/projects')).data.some((x) => x.id === pT.id), '恢复后回到列表');
  await api('DELETE', `/api/projects/${pT.id}?purge=1`);
  ok(!(await api('GET', '/api/projects/trash')).data.some((x) => x.id === pT.id), '彻底删除后回收站不可见');
  const retryBad = await api('POST', `/api/ai/task/${vid.taskId}/retry`, {});
  ok(retryBad.status === 400 && /force/.test(retryBad.error || ''), '未失败任务拒绝普通重试');
  const retried = (await api('POST', `/api/ai/task/${vid.taskId}/retry`, { force: true })).data;
  const retriedDone = await until(async () => {
    const t = (await api('GET', `/api/ai/task/${retried.taskId}`)).data;
    return t.status === 'succeeded' ? t : null;
  });
  ok(retriedDone.result.url.startsWith('/uploads/'), '强制重出生成新任务并完成');

  console.log('— 设置 —');
  const set1 = await api('PATCH', '/api/settings', { ark_api_key: 'AKLTxxxx' });
  ok(set1.status === 400, '拦截 AccessKey 误填');
  const set2 = (await api('PATCH', '/api/settings', { user_name: '导演' }));
  ok(set2.ok, '保存偏好');
  const set3 = (await api('GET', '/api/settings')).data;
  ok(set3.user_name === '导演', '设置生效');
  await api('PATCH', '/api/settings', { model_image_pro: 'ep-pro-test-xyz' });
  ok((await api('GET', '/api/settings')).data.model_image_pro === 'ep-pro-test-xyz', '顶配图像模型可配置并生效');
  await api('PATCH', '/api/settings', { model_image_pro: '' });   // 复位，避免影响其它用例
  // OpenAI / Google 各自独立 API Key：脱敏保存 + 启用状态 + 接口地址
  await api('PATCH', '/api/settings', { openai_api_key: 'sk-test-12345678', openai_base_url: 'https://oai.example/v1', google_api_key: 'gk-test-abcdefgh', google_base_url: 'https://g.example/v1beta' });
  const setProv = (await api('GET', '/api/settings')).data;
  ok(setProv.openai_api_key_masked.includes('****') && setProv.openai_enabled === true && setProv.openai_base_url === 'https://oai.example/v1', 'OpenAI Key 脱敏保存、启用、接口地址生效');
  ok(setProv.google_api_key_masked.includes('****') && setProv.google_enabled === true, 'Google Key 脱敏保存并启用');
  await api('PATCH', '/api/settings', { openai_api_key: 'clear', google_api_key: 'clear' });   // 复位，避免真实外呼
  ok((await api('GET', '/api/settings')).data.openai_enabled === false, '清除 OpenAI Key 后回到未配置');
  // 阿里云百炼·统一 Key（千问 + 通义万相）：脱敏保存 + 启用 + 接口地址
  await api('PATCH', '/api/settings', { dashscope_api_key: 'sk-dash-test-1234', dashscope_base_url: 'https://ds.example' });
  const setDash = (await api('GET', '/api/settings')).data;
  ok(setDash.dashscope_api_key_masked.includes('****') && setDash.alibaba_enabled === true && setDash.dashscope_base_url === 'https://ds.example', '阿里 DashScope Key 脱敏保存、启用、接口地址生效');
  // 选千问对话 + 配 DashScope Key → 对话大模型可用（统一 API：千问走 DashScope 兼容端点）
  await api('PATCH', '/api/settings', { model_chat: 'qwen-max' });
  ok((await api('GET', '/api/bootstrap')).data.llm_enabled === true, '选千问 + 配 DashScope Key → 对话大模型可用（llm_enabled）');
  await api('PATCH', '/api/settings', { model_chat: 'doubao-seed-1-6-250615', dashscope_api_key: 'clear' });   // 复位，避免真实外呼
  ok((await api('GET', '/api/settings')).data.alibaba_enabled === false, '清除 DashScope Key 后回到未配置');
  // Vidu 全能参考 Key：脱敏保存 + 启用 + 接口地址
  await api('PATCH', '/api/settings', { vidu_api_key: 'vidu-test-key-1234', vidu_base_url: 'https://vidu.example' });
  const setVidu = (await api('GET', '/api/settings')).data;
  ok(setVidu.vidu_api_key_masked.includes('****') && setVidu.vidu_enabled === true && setVidu.vidu_base_url === 'https://vidu.example', 'Vidu Key 脱敏保存、启用、接口地址生效');
  ok((await api('GET', '/api/bootstrap')).data.providers.vidu === true, 'bootstrap 反映 Vidu 已开通');
  await api('PATCH', '/api/settings', { vidu_api_key: 'clear' });   // 复位，避免真实外呼
  ok((await api('GET', '/api/settings')).data.vidu_enabled === false, '清除 Vidu Key 后回到未配置');
  // 可灵 Kling：AK/SK 双密钥，两者齐备才启用
  await api('PATCH', '/api/settings', { kling_access_key: 'kl-ak-test-1234', kling_secret_key: 'kl-sk-test-5678' });
  const setKling = (await api('GET', '/api/settings')).data;
  ok(setKling.kling_access_key_masked.includes('****') && setKling.kling_secret_key_masked.includes('****') && setKling.kling_enabled === true, '可灵 AK/SK 脱敏保存并启用');
  await api('PATCH', '/api/settings', { kling_secret_key: 'clear' });
  ok((await api('GET', '/api/settings')).data.kling_enabled === false, '仅 AK 无 SK 时可灵不启用（需双密钥）');
  await api('PATCH', '/api/settings', { kling_access_key: 'clear' });   // 复位
  // 墨行AI 聚合站：脱敏保存 + 启用 + 接口地址
  await api('PATCH', '/api/settings', { moxing_api_key: 'sk-moxing-test-1234', moxing_base_url: 'https://moxing.example/v1' });
  const setMox = (await api('GET', '/api/settings')).data;
  ok(setMox.moxing_api_key_masked.includes('****') && setMox.moxing_enabled === true && setMox.moxing_base_url === 'https://moxing.example/v1', '墨行AI Key 脱敏保存、启用、接口地址生效');
  ok((await api('GET', '/api/bootstrap')).data.providers.moxing === true, 'bootstrap 反映 墨行AI 已开通');
  await api('PATCH', '/api/settings', { moxing_api_key: 'clear' });   // 复位，避免真实外呼
  ok((await api('GET', '/api/settings')).data.moxing_enabled === false, '清除 墨行AI Key 后回到未配置');
  const stats = (await api('GET', '/api/stats')).data;
  ok(Number(stats.cost_total_yuan) === 0, '本地模式成本为 0');

  console.log('— MCP Server（stdio 端到端） —');
  const mcp = spawn(process.execPath, [path.join(ROOT, 'mcp', 'server.mjs')], {
    env: { ...process.env, LINGJING_BASE: BASE, LINGJING_TOKEN: token },
    stdio: ['pipe', 'pipe', 'ignore']
  });
  const mcpReplies = new Map();
  let buf = '';
  mcp.stdout.on('data', (d) => {
    buf += String(d);
    let idx;
    while ((idx = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, idx); buf = buf.slice(idx + 1);
      if (!line.trim()) continue;
      try { const m = JSON.parse(line); if (m.id !== undefined) mcpReplies.set(m.id, m); } catch { /* noop */ }
    }
  });
  const mcpSend = (m) => mcp.stdin.write(JSON.stringify(m) + '\n');
  const mcpWait = (id) => until(() => mcpReplies.get(id), 8000);
  mcpSend({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18' } });
  const init = await mcpWait(1);
  ok(init.result.serverInfo.name === 'lingjing-studio', 'MCP initialize');
  ok(init.result.protocolVersion === '2025-06-18', 'MCP 回显协议版本');
  mcpSend({ jsonrpc: '2.0', method: 'notifications/initialized' });
  mcpSend({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
  const tl = await mcpWait(2);
  ok(tl.result.tools.length >= 14 && tl.result.tools[0].inputSchema, 'MCP tools/list');
  mcpSend({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'list_projects', arguments: {} } });
  const tc = await mcpWait(3);
  ok(tc.result.content[0].text.includes('冒烟剧'), 'MCP tools/call 取到真实数据');
  mcpSend({ jsonrpc: '2.0', id: 4, method: 'ping' });
  ok((await mcpWait(4)) && true, 'MCP ping');
  mcp.kill();
} catch (e) {
  failed++;
  console.error('  ✗ 异常中断：', e.message);
} finally {
  server.kill();
  fs.rmSync(TMP, { recursive: true, force: true });
}

console.log(`\n${failed ? '❌' : '✅'} 灵境AI冒烟测试：${passed} 通过 / ${failed} 失败\n`);
process.exit(failed ? 1 : 0);
