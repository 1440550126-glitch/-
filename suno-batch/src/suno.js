// SUNO 页面操作封装：登录态复用、进入 Custom 模式、填 歌词/曲风/歌名、点生成、判定接受/额度不足。
// 关键设计：每个元素都用「一组候选选择器」逐个尝试，命中即用——SUNO 改版时只坏一个不至于全盘崩。
import { chromium } from 'playwright';
import { config } from './config.js';

const T = config.timing.actionTimeoutMs;

// 从候选选择器里找到第一个可见元素；找不到返回 null。
async function firstVisible(page, selectors, timeout = 3000) {
  for (const sel of selectors) {
    try {
      const loc = page.locator(sel).first();
      await loc.waitFor({ state: 'visible', timeout });
      return loc;
    } catch { /* 试下一个 */ }
  }
  return null;
}

export async function launch() {
  const context = await chromium.launchPersistentContext(config.browser.userDataDir, {
    headless: config.browser.headless,
    viewport: { width: 1280, height: 900 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  context.setDefaultTimeout(T);
  const page = context.pages()[0] || await context.newPage();
  return { context, page };
}

export async function gotoCreate(page) {
  await page.goto(config.createUrl, { waitUntil: 'domcontentloaded', timeout: T });
  await page.waitForTimeout(1500);
}

// 是否停在登录墙。用于首启动引导用户手动登录一次。
export async function isLoginWall(page) {
  const wall = await firstVisible(page, config.selectors.loginWall, 1500);
  const custom = await firstVisible(page, config.selectors.customTab, 1500);
  return !!wall && !custom;
}

// 等待用户在弹出的窗口里手动完成登录，直到创作界面出现（每 3 秒轮询，最长 5 分钟）。
export async function waitForLogin(page, onTick) {
  const deadline = Date.now() + 5 * 60_000;
  while (Date.now() < deadline) {
    await gotoCreate(page);
    if (!(await isLoginWall(page))) return true;
    onTick?.();
    await page.waitForTimeout(3000);
  }
  return false;
}

async function enterCustomMode(page) {
  const tab = await firstVisible(page, config.selectors.customTab, 4000);
  if (tab) { try { await tab.click({ timeout: 4000 }); await page.waitForTimeout(600); } catch {} }
}

async function fillField(page, selectors, value, name) {
  const loc = await firstVisible(page, selectors, 5000);
  if (!loc) throw new Error(`找不到「${name}」输入框——SUNO 可能改版了，跑 npm run inspect 后更新 config.json 里的 ${name} 选择器`);
  await loc.click({ timeout: T });
  await loc.fill('');            // 清空旧内容
  await loc.fill(value || '');
  await page.waitForTimeout(200);
}

async function setInstrumental(page, want) {
  const toggle = await firstVisible(page, config.selectors.instrumentalToggle, 2000);
  if (!toggle) return;
  try {
    const state = await toggle.getAttribute('aria-checked');
    const isOn = state === 'true';
    if (isOn !== want) { await toggle.click({ timeout: 4000 }); await page.waitForTimeout(300); }
  } catch { /* 拿不到状态就不硬切，避免误操作 */ }
}

// 填一首歌的所有字段。dryRun=true 时只填不点生成。
export async function fillSong(page, song, { dryRun = false } = {}) {
  await enterCustomMode(page);
  await setInstrumental(page, !!song.instrumental);
  if (!song.instrumental) await fillField(page, config.selectors.lyrics, song.lyrics, 'lyrics');
  await fillField(page, config.selectors.style, song.style, 'style');
  await fillField(page, config.selectors.title, song.title, 'title');
  if (dryRun) return { clicked: false };

  const btn = await firstVisible(page, config.selectors.createButton, 5000);
  if (!btn) throw new Error('找不到「生成/Create」按钮——跑 npm run inspect 更新 config.json 的 createButton 选择器');
  await btn.click({ timeout: T });
  return { clicked: true };
}

// 点了生成后，在 acceptWaitMs 内判定：出现额度不足/超限 → 拦截；否则视为已提交。
export async function waitAccepted(page) {
  const err = await firstVisible(page, config.selectors.errorToast, config.timing.acceptWaitMs);
  if (err) {
    let msg = '';
    try { msg = (await err.innerText()).slice(0, 120); } catch {}
    const low = msg.toLowerCase();
    const outOfCredits = /credit|额度|insufficient|not enough/.test(low);
    return { accepted: false, outOfCredits, message: msg || '出现错误提示' };
  }
  return { accepted: true };
}

export async function readCredits(page) {
  const badge = await firstVisible(page, config.selectors.creditsBadge, 1500);
  if (!badge) return null;
  try { return (await badge.innerText()).replace(/\s+/g, ' ').trim().slice(0, 40); } catch { return null; }
}
