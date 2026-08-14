// 浏览器会话管理：单账号或多账号轮换的统一入口，被 run/panel/scheduler 共用。
// - session 是可变对象 { context, page, harvest, account }，engine 每轮从中读当前 page/harvest。
// - rotate() 切到下一个账号（额度耗尽时用）；没有更多账号则返回 null（由调用方转为暂停）。
// - download=true 时给每个账号挂 harvest，并共享 clips/downloaded/titlePlaylist，使质检与去重贯通全账号。
import { chromium } from 'playwright';
import { resolve } from 'node:path';
import { config } from './config.js';
import * as suno from './suno.js';
import { attachHarvest } from './harvest.js';

export function listAccounts() {
  const dirs = config.accounts.length ? config.accounts : [process.env.USER_DATA_DIR || '.suno-profile'];
  return dirs.map(d => ({ name: d, userDataDir: resolve(config.root, d) }));
}

// 逐个账号打开浏览器让用户登录一次（登录态各自持久化到自己的目录）。
export async function loginAll(onLog = () => {}) {
  const accounts = listAccounts();
  for (const acc of accounts) {
    const context = await chromium.launchPersistentContext(acc.userDataDir, { headless: false, viewport: { width: 1280, height: 900 } });
    try {
      const page = context.pages()[0] || await context.newPage();
      await suno.gotoCreate(page);
      if (await suno.isLoginWall(page)) {
        onLog(`账号「${acc.name}」请在窗口登录…`);
        const ok = await suno.waitForLogin(page, () => onLog(`[${acc.name}] 等待登录…`));
        onLog(ok ? `✅ 账号「${acc.name}」登录成功` : `❌ 账号「${acc.name}」超时未登录`);
      } else onLog(`✅ 账号「${acc.name}」已是登录态`);
    } finally { await context.close().catch(() => {}); }
  }
}

export async function openSession({ headless = config.browser.headless, download = false, rotate = false, onLog = () => {} } = {}) {
  const accounts = rotate ? listAccounts() : [{ name: process.env.USER_DATA_DIR || '.suno-profile', userDataDir: config.browser.userDataDir }];
  const shared = download ? {} : null;                 // 跨账号共享的下载/质检状态
  const session = { context: null, page: null, harvest: null, account: null };
  let idx = -1;

  async function openAt(i) {
    if (session.context) await session.context.close().catch(() => {});
    const acc = accounts[i];
    const context = await chromium.launchPersistentContext(acc.userDataDir, {
      headless, viewport: { width: 1280, height: 900 },
      args: ['--disable-blink-features=AutomationControlled'],
    });
    context.setDefaultTimeout(config.timing.actionTimeoutMs);
    const page = context.pages()[0] || await context.newPage();
    await suno.gotoCreate(page);
    if (await suno.isLoginWall(page)) {
      onLog(`账号「${acc.name}」需要登录，请在浏览器窗口完成…`);
      if (!await suno.waitForLogin(page, () => onLog('仍在等待登录…'))) return false;
    }
    session.context = context; session.page = page; session.account = acc;
    session.harvest = download ? attachHarvest(context, page, shared) : null;
    onLog(`✅ 账号「${acc.name}」就绪` + (accounts.length > 1 ? `（${i + 1}/${accounts.length}）` : ''));
    return true;
  }

  if (!await openAt(0)) throw new Error('首个账号登录失败');
  idx = 0;

  return {
    session,
    accounts,
    multi: accounts.length > 1,
    // 切换到下一个账号；成功返回新 page，无更多账号返回 null
    async rotate() {
      if (idx >= accounts.length - 1) { onLog('已无更多账号可切换。'); return null; }
      idx++;
      onLog(`↪ 额度耗尽，切换到账号「${accounts[idx].name}」…`);
      if (!await openAt(idx)) return null;
      return session.page;
    },
    getClips: () => (session.harvest ? session.harvest.getClips() : []),
    async close() { if (session.context) await session.context.close().catch(() => {}); },
  };
}
