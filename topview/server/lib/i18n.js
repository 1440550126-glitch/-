// 爆款工厂 · 视频本地化：把分镜的字幕/口播翻译成目标语言并生成分语言 SRT（对标 TopView 多语言）
import { chat, llmEnabled } from './llm.js';
import { srtTime } from './util.js';

// 常用出海语言（可继续扩充；id 用于 TTS voice 选择与 SRT 命名）
export const LANGS = [
  { id: 'zh', name: '简体中文' }, { id: 'en', name: 'English' }, { id: 'ja', name: '日本語' },
  { id: 'ko', name: '한국어' }, { id: 'es', name: 'Español' }, { id: 'pt', name: 'Português' },
  { id: 'fr', name: 'Français' }, { id: 'de', name: 'Deutsch' }, { id: 'id', name: 'Bahasa Indonesia' },
  { id: 'th', name: 'ไทย' }, { id: 'vi', name: 'Tiếng Việt' }, { id: 'ar', name: 'العربية' },
  { id: 'ru', name: 'Русский' }, { id: 'it', name: 'Italiano' }, { id: 'tr', name: 'Türkçe' }
];
export const langName = (id) => LANGS.find((l) => l.id === id)?.name || id;

/** 翻译分镜文案到目标语言。配了模型走真实翻译，否则本地透传并标注「待译」。 */
export async function translateShots(shots = [], targetLang = 'en', { sourceLang = 'zh' } = {}) {
  const items = shots.map((s) => ({ key: s.key, onscreen: s.onscreen || '', voiceover: s.voiceover || '' }));
  if (targetLang === sourceLang) return { shots: items, byLLM: false };
  if (llmEnabled()) {
    try {
      const sys = `你是专业的电商广告本地化译员。把给定 JSON 中每条的 onscreen(屏幕字幕) 与 voiceover(口播) 翻译成 ${langName(targetLang)}，保留营销语气与节奏，屏幕字幕要短。只输出同结构 JSON：{"shots":[{"key","onscreen","voiceover"}]}。`;
      const { text } = await chat({ system: sys, prompt: JSON.stringify({ shots: items }), json: true, feature: 'translate', temperature: 0.5 });
      const data = JSON.parse(text);
      const map = new Map((data.shots || []).map((s) => [s.key, s]));
      const out = items.map((s) => ({ key: s.key, onscreen: String(map.get(s.key)?.onscreen || s.onscreen).slice(0, 80), voiceover: String(map.get(s.key)?.voiceover || s.voiceover).slice(0, 240) }));
      return { shots: out, byLLM: true };
    } catch { /* 失败兜底 */ }
  }
  // 本地兜底：透传 + 标注（接入大模型后自动翻译）
  const out = items.map((s) => ({ key: s.key, onscreen: s.onscreen, voiceover: s.voiceover, untranslated: true }));
  return { shots: out, byLLM: false };
}

/** 用分镜时长排时间轴，生成 SRT 字幕（屏幕字幕优先，没有则用口播） */
export function buildSrt(shots = [], localizedShots = null) {
  const locMap = new Map((localizedShots || []).map((s) => [s.key, s]));
  let t = 0; const lines = [];
  shots.forEach((s, i) => {
    const dur = Math.max(1, Number(s.duration) || 4);
    const loc = locMap.get(s.key);
    const text = (loc?.onscreen || loc?.voiceover || s.onscreen || s.voiceover || '').trim();
    lines.push(`${i + 1}\n${srtTime(t)} --> ${srtTime(t + dur)}\n${text}\n`);
    t += dur;
  });
  return lines.join('\n');
}
