// 大模型内容生成：给主题/关键词 → 产出 SUNO 友好的 歌名 / 曲风标签 / 分段歌词。
// OpenAI 兼容 /chat/completions，Node 内置 fetch，零依赖。
import { config } from './config.js';

const SYSTEM = `你是专业的词曲策划，为 AI 音乐平台 SUNO 生成创作输入。
严格返回 JSON（不要任何解释、不要 markdown 代码块），字段：
{
  "title": "简短有记忆点的歌名，不带书名号",
  "style": "英文为主的曲风/风格标签，逗号分隔，包含流派+人声/器乐+情绪+节奏，例如 'city pop, female vocal, dreamy, 90bpm'。这是喂给 SUNO 的 Style of Music，务必精炼且是它认识的音乐术语",
  "lyrics": "带段落标记的完整歌词。用 [Verse] [Chorus] [Bridge] [Outro] 等英文段落标记，正文用指定语言。结构完整、有记忆点、可传唱；纯器乐时给空字符串"
}`;

function buildUser(task) {
  const lang = task.language || config.llm.language || '中文';
  const mood = task.mood || config.llm.mood || '';
  const lines = [
    `主题/灵感：${task.theme || task.title || '自由发挥'}`,
    task.genre ? `期望曲风：${task.genre}` : '',
    `歌词语言：${lang}`,
    mood ? `情绪基调：${mood}` : '',
    task.instrumental ? '这是纯器乐曲目：lyrics 返回空字符串，style 里体现无人声。' : '',
    task.title ? `已定歌名（沿用）：${task.title}` : '',
    task.style ? `已定曲风（可微调）：${task.style}` : '',
  ].filter(Boolean);
  return lines.join('\n');
}

function extractJson(s) {
  const a = s.indexOf('{'), b = s.lastIndexOf('}');
  if (a >= 0 && b > a) return JSON.parse(s.slice(a, b + 1));
  return JSON.parse(s);
}

// 生成缺失字段。已在 CSV 里填好的 title/style/lyrics 会被保留，只补空缺。
export async function generate(task, { retries = 2 } = {}) {
  // 三项都齐了就不必调用大模型
  const needLyrics = !task.instrumental && !task.lyrics;
  if (task.title && task.style && (task.instrumental || task.lyrics)) {
    return { title: task.title, style: task.style, lyrics: task.lyrics };
  }
  if (!config.llm.apiKey) {
    throw new Error('缺少 LLM_API_KEY：CSV 里有字段留空需要大模型生成，请在 .env 配置，或把 title/style/lyrics 都填满。');
  }
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(`${config.llm.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${config.llm.apiKey}` },
        body: JSON.stringify({
          model: config.llm.model,
          temperature: 0.9,
          messages: [
            { role: 'system', content: SYSTEM },
            { role: 'user', content: buildUser(task) },
          ],
        }),
      });
      if (!res.ok) throw new Error(`LLM HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
      const data = await res.json();
      const content = data?.choices?.[0]?.message?.content || '';
      const out = extractJson(content);
      return {
        title: (task.title || out.title || '').toString().trim().slice(0, 80),
        style: (task.style || out.style || '').toString().trim().slice(0, 200),
        lyrics: task.instrumental ? '' : (task.lyrics || out.lyrics || '').toString().trim(),
      };
    } catch (e) {
      lastErr = e;
      if (attempt < retries) await new Promise(r => setTimeout(r, 1200 * (attempt + 1)));
    }
  }
  throw new Error(`大模型生成失败（已重试）：${lastErr?.message || lastErr}`);
}
