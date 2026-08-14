// 配置加载：读 .env（零依赖手写解析）+ config.json，合并出运行期配置。
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
export const ROOT = resolve(__dirname, '..');

function loadDotenv(file) {
  if (!existsSync(file)) return;
  for (const raw of readFileSync(file, 'utf8').split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq < 0) continue;
    const key = line.slice(0, eq).trim();
    let val = line.slice(eq + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    if (process.env[key] === undefined) process.env[key] = val;
  }
}

loadDotenv(join(ROOT, '.env'));

const json = JSON.parse(readFileSync(join(ROOT, 'config.json'), 'utf8'));
const num = (v, d) => (v !== undefined && v !== '' && !Number.isNaN(Number(v)) ? Number(v) : d);

export const config = {
  root: ROOT,
  createUrl: json.createUrl,
  selectors: json.selectors,
  timing: {
    betweenSongsMs: num(process.env.BETWEEN_SONGS_MS, json.timing.betweenSongsMs),
    acceptWaitMs: num(process.env.ACCEPT_WAIT_MS, json.timing.acceptWaitMs),
    actionTimeoutMs: num(process.env.ACTION_TIMEOUT_MS, json.timing.actionTimeoutMs),
  },
  browser: {
    userDataDir: resolve(ROOT, process.env.USER_DATA_DIR || '.suno-profile'),
    headless: String(process.env.HEADLESS || 'false').toLowerCase() === 'true',
  },
  llm: {
    baseUrl: (process.env.LLM_BASE_URL || '').replace(/\/$/, ''),
    apiKey: process.env.LLM_API_KEY || '',
    model: process.env.LLM_MODEL_DEFAULT || 'gpt-4o-mini',
    language: process.env.DEFAULT_LANGUAGE || '中文',
    mood: process.env.DEFAULT_MOOD || '',
  },
  retry: {
    max: num(process.env.RETRY_MAX, 2),            // 单首失败自动重试次数
    backoffMs: num(process.env.RETRY_BACKOFF_MS, 8000),
  },
  daily: {
    at: process.env.DAILY_AT || '03:00',           // 每日定时挂机时间 HH:MM（本地时区）
    limit: num(process.env.DAILY_LIMIT, 0),        // 每天最多生成几首（0=不限，跑完待处理为止）
  },
};
