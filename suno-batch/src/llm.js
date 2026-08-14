// 大模型内容生成：给主题/关键词 → 产出 **完全对齐 SUNO 标准** 的 歌名 / 曲风标签 / 分段歌词。
// 标准细节见 references/suno-lyric-standard.md。OpenAI 兼容 /chat/completions，Node 内置 fetch，零依赖。
import { config } from './config.js';

const LYRICS_MAX = 3000;   // SUNO 歌词字符上限留余量
const STYLE_MAX = 200;     // Style of Music 字段建议上限

// 语言模式归一化：中文 / 英文 / 双语
export function normalizeLanguage(raw) {
  const s = String(raw || '').trim().toLowerCase();
  if (/双语|中英|bilingual|zh.?en|en.?zh|mix/.test(s)) return 'bilingual';
  if (/英|english|^en$|us|uk/.test(s)) return 'english';
  return 'chinese'; // 默认中文
}

const LANG_RULE = {
  chinese: '歌词正文全部用中文（结构标签仍用英文方括号）。',
  english: 'Write all lyric lines in natural, singable English (structure tags in English brackets).',
  bilingual:
    '双语模式：主歌（Verse）用中文叙事，副歌（Chorus/Hook）用英文做记忆点，可在括号里加另一语言的呼应；' +
    '整体要自然、可唱、不生硬。结构标签用英文方括号。',
};

const SYSTEM = `你是资深词曲人，专为 AI 音乐平台 SUNO 产出创作输入。严格遵循 SUNO 歌词标准：

【结构】歌词用英文方括号标注段落，标签不唱出：[Intro] [Verse] [Pre-Chorus] [Chorus] [Post-Chorus] [Hook] [Bridge] [Break] [Instrumental] [Guitar Solo] [Outro]。
至少含 [Verse] 和 [Chorus]，推荐 3–5 段的完整走向（如 Verse→Pre-Chorus→Chorus→Verse→Chorus→Bridge→Chorus→Outro，不必全用）。
【演唱细节】和声/加花/回声/气声放圆括号，如 (oooh)、(still here)、(echo)。
【可制作提示】需要时段落前加情绪/编曲方括号提示，如 [Whispered] [Building intensity] [Powerful vocals] [Soft piano] [Beat drop]。
【硬约束】歌词总字符 < ${LYRICS_MAX}；每行可唱、口语顺、有韵脚与记忆点；副歌要能传唱。纯器乐则 lyrics 为空字符串。

【曲风 style】喂给 SUNO「Style of Music」框：英文为主、逗号分隔、≤${STYLE_MAX} 字符，覆盖「流派, 人声类型, 情绪, 乐器/制作, 速度(bpm)」。
绝不写任何歌手/乐队真名（会被过滤），改用风格描述（如 mandopop, R&B-influenced, dreamy synth, 90bpm）。纯器乐要含 instrumental, no vocals。
【歌名 title】短、有记忆点、不带书名号，语言跟随歌曲基调。

只返回 JSON，禁止解释、禁止 markdown 代码块：
{"title":"...","style":"...","lyrics":"..."}`;

function buildUser(task) {
  const lang = normalizeLanguage(task.language || config.llm.language);
  const mood = task.mood || config.llm.mood || '';
  const lines = [
    `主题/灵感：${task.theme || task.title || '自由发挥'}`,
    task.genre ? `期望曲风：${task.genre}` : '',
    `语言模式：${LANG_RULE[lang]}`,
    mood ? `情绪基调：${mood}` : '',
    task.instrumental ? '这是纯器乐曲目：lyrics 返回空字符串，style 必含 instrumental, no vocals。' : '',
    task.title ? `已定歌名（沿用，不要改）：${task.title}` : '',
    task.style ? `已定曲风（可微调补全维度）：${task.style}` : '',
    task.lyrics ? '已提供部分歌词，请在其基础上按 SUNO 结构标准补全成完整歌词。' : '',
    task.lyrics ? `已有歌词片段：\n${task.lyrics}` : '',
  ].filter(Boolean);
  return lines.join('\n');
}

function extractJson(s) {
  // 容错：剥掉可能的 ```json 包裹，再截取第一个 { 到最后一个 }
  const cleaned = s.replace(/```json/gi, '').replace(/```/g, '');
  const a = cleaned.indexOf('{'), b = cleaned.lastIndexOf('}');
  if (a >= 0 && b > a) return JSON.parse(cleaned.slice(a, b + 1));
  return JSON.parse(cleaned);
}

// 生成缺失字段。已在 CSV 里填好的 title/style/lyrics 优先保留，只补空缺；歌词若只给了片段也会补全。
export async function generate(task, { retries = 2 } = {}) {
  const complete = task.title && task.style && (task.instrumental || task.lyrics);
  // 三项齐全且歌词看起来已带结构标签，则不调用大模型
  if (complete && (task.instrumental || /\[[A-Za-z]/.test(task.lyrics))) {
    return { title: task.title, style: task.style, lyrics: task.instrumental ? '' : task.lyrics };
  }
  if (!config.llm.apiKey) {
    throw new Error('缺少 LLM_API_KEY：有字段需大模型生成，请在 .env 配置，或把 title/style/lyrics 都按 SUNO 结构填满。');
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
      return validate({
        title: (task.title || out.title || '').toString().trim().slice(0, 80),
        style: (task.style || out.style || '').toString().trim(),
        lyrics: task.instrumental ? '' : (out.lyrics || task.lyrics || '').toString().trim(),
      }, task);
    } catch (e) {
      lastErr = e;
      if (attempt < retries) await new Promise(r => setTimeout(r, 1200 * (attempt + 1)));
    }
  }
  throw new Error(`大模型生成失败（已重试）：${lastErr?.message || lastErr}`);
}

// 轻校验 + 兜底修正，保证不违反 SUNO 硬约束。
export function validate(s, task = {}) {
  const warnings = [];
  // 曲风裁剪到上限
  if (s.style.length > STYLE_MAX) { s.style = s.style.slice(0, STYLE_MAX).replace(/,[^,]*$/, ''); warnings.push('style 超长已裁剪'); }
  if (task.instrumental && !/instrumental|no vocals/i.test(s.style)) s.style += (s.style ? ', ' : '') + 'instrumental, no vocals';
  if (!task.instrumental) {
    // 歌词字数上限
    if (s.lyrics.length > LYRICS_MAX) { s.lyrics = s.lyrics.slice(0, LYRICS_MAX); warnings.push('lyrics 超长已裁剪'); }
    // 缺结构标签则补最小结构，避免 SUNO 把整段当一坨
    if (!/\[[A-Za-z]/.test(s.lyrics) && s.lyrics) { s.lyrics = `[Verse]\n${s.lyrics}`; warnings.push('已补 [Verse] 标签'); }
    if (!/\[chorus\]/i.test(s.lyrics)) warnings.push('无 [Chorus]，建议检查副歌');
  }
  s.warnings = warnings;
  return s;
}
