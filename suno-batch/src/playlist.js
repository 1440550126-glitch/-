// 把生成好的歌加入 SUNO 歌单（best-effort UI 自动化）。
// 依赖 SUNO 资料库页面结构，改版可能失效——失效时静默跳过、不影响其它流程，
// 可退回手动加歌单。选择器集中在 config.json 的 selectors.playlist.*。
import { config } from './config.js';

const T = config.timing.actionTimeoutMs;

async function firstVisible(scope, selectors, timeout = 3000) {
  for (const sel of selectors || []) {
    try { const loc = scope.locator(sel).first(); await loc.waitFor({ state: 'visible', timeout }); return loc; }
    catch {}
  }
  return null;
}

// 为若干 {title, playlist} 目标做一次归类 pass。report(event,data) 上报进度。
export async function assignPlaylists(page, targets, report = () => {}) {
  const sel = config.selectors.playlist || {};
  if (!sel.libraryUrl) { report('log', { message: '未配置歌单选择器，跳过 SUNO 歌单归类（本地索引仍会生成）。' }); return; }
  let ok = 0, miss = 0;
  const byName = new Map();
  for (const t of targets) { if (!t.playlist) continue; if (!byName.has(t.playlist)) byName.set(t.playlist, []); byName.get(t.playlist).push(t.title); }

  for (const [playlist, titles] of byName) {
    for (const title of titles) {
      try {
        await page.goto(sel.libraryUrl, { waitUntil: 'domcontentloaded', timeout: T });
        await page.waitForTimeout(1000);
        // 搜索该曲
        const search = await firstVisible(page, sel.search, 3000);
        if (search) { await search.fill(title); await page.waitForTimeout(1200); }
        // 定位歌曲行
        const row = await firstVisible(page, (sel.rowByTitle || []).map(s => s.replace('{title}', title)), 4000);
        if (!row) { miss++; report('playlist', { title, playlist, ok: false }); continue; }
        // 打开更多菜单 → 加入歌单
        const menu = await firstVisible(row, sel.rowMenu, 3000) || await firstVisible(page, sel.rowMenu, 3000);
        if (menu) { await menu.click({ timeout: T }); await page.waitForTimeout(500); }
        const addBtn = await firstVisible(page, sel.addToPlaylist, 3000);
        if (!addBtn) { miss++; report('playlist', { title, playlist, ok: false }); continue; }
        await addBtn.click({ timeout: T }); await page.waitForTimeout(600);
        // 在歌单弹窗里选/建歌单
        const plSearch = await firstVisible(page, sel.playlistSearch, 2500);
        if (plSearch) { await plSearch.fill(playlist); await page.waitForTimeout(800); }
        const pick = await firstVisible(page, (sel.playlistOption || []).map(s => s.replace('{name}', playlist)), 3000)
          || await firstVisible(page, sel.createPlaylist, 3000);
        if (pick) { await pick.click({ timeout: T }); await page.waitForTimeout(800); ok++; report('playlist', { title, playlist, ok: true }); }
        else { miss++; report('playlist', { title, playlist, ok: false }); }
      } catch { miss++; report('playlist', { title, playlist, ok: false }); }
    }
  }
  report('playlist-done', { ok, miss });
  return { ok, miss };
}
