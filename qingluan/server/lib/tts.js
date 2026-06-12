// 青鸾 · 火山引擎语音合成（配音）
// 文档：火山引擎控制台 → 语音技术 → 音频生成（离线语音合成 HTTP 接口）
// 凭证：AppID + Access Token（与方舟 API Key 不同体系）；未配置时接口报错并引导，
//      放映室的浏览器朗读不受影响。接口地址/音色/集群均可在设置页覆盖。
import fs from 'node:fs';
import path from 'node:path';
import { getSetting, UPLOAD_DIR } from './db.js';
import { uid } from './util.js';
import { bad } from './httpx.js';
import { logUsage } from './ark.js';

const DEFAULTS = {
  endpoint: 'https://openspeech.bytedance.com/api/v1/tts',
  cluster: 'volcano_tts',
  voice: 'BV001_streaming'      // 通用女声；男声 BV002_streaming，更多音色见控制台音色列表
};

export function ttsCfg() {
  const g = (key, envKey, dft) => {
    const v = getSetting(key, null);
    if (v !== null && v !== '') return v;
    if (envKey && process.env[envKey]) return process.env[envKey];
    return dft;
  };
  return {
    appid: g('tts_appid', 'VOLC_TTS_APPID', ''),
    token: g('tts_token', 'VOLC_TTS_TOKEN', ''),
    voice: g('tts_voice', 'VOLC_TTS_VOICE', DEFAULTS.voice),
    cluster: g('tts_cluster', '', DEFAULTS.cluster),
    endpoint: g('tts_endpoint', '', DEFAULTS.endpoint)
  };
}
export const ttsEnabled = () => {
  const c = ttsCfg();
  return !!(c.appid && c.token);
};

/** 合成一段台词为 mp3，落盘 uploads，返回 /uploads/xxx.mp3 */
export async function synthesize(text, { voice = '' } = {}) {
  const c = ttsCfg();
  if (!ttsEnabled()) {
    throw bad('未配置火山语音合成：到设置页填 TTS AppID 与 Access Token（火山引擎控制台 → 语音技术 → 语音合成）。放映室的浏览器朗读不受影响');
  }
  const clean = String(text || '').trim().slice(0, 300);
  if (!clean) throw bad('台词为空，无法配音');
  const resp = await fetch(c.endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer;${c.token}` },
    body: JSON.stringify({
      app: { appid: c.appid, token: c.token, cluster: c.cluster },
      user: { uid: 'qingluan' },
      audio: { voice_type: voice || c.voice, encoding: 'mp3', speed_ratio: 1.0 },
      request: { reqid: uid('tts'), text: clean, operation: 'query' }
    }),
    signal: AbortSignal.timeout(30_000)
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok || !data?.data) {
    throw bad(`语音合成失败：${data?.message || data?.Message || `code ${data?.code ?? resp.status}`}（确认音色已开通、Token 未过期）`);
  }
  const name = `${uid('dub')}.mp3`;
  fs.writeFileSync(path.join(UPLOAD_DIR, name), Buffer.from(data.data, 'base64'));
  logUsage({ feature: 'tts', provider: 'volc-tts', model: voice || c.voice, promptTokens: [...clean].length });
  return `/uploads/${name}`;
}
