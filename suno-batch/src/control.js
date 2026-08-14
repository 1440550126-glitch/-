// 终端控制台：热键 p=暂停/继续  s=跳过当前等待  q=优雅退出。附一个可被暂停/跳过打断的倒计时 sleep。
import readline from 'node:readline';

export function createControl() {
  const state = { paused: false, quit: false, skipWait: false };
  let wakeSkip = null, wakePause = null;

  if (process.stdin.isTTY) {
    readline.emitKeypressEvents(process.stdin);
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.on('keypress', (_str, key) => {
      if (!key) return;
      if (key.ctrl && key.name === 'c') { state.quit = true; wakeSkip?.(); wakePause?.(); return; }
      if (key.name === 'p') {
        state.paused = !state.paused;
        log(state.paused ? '⏸  已暂停（按 p 继续）' : '▶  继续');
        if (!state.paused) wakePause?.();
      } else if (key.name === 's') { state.skipWait = true; wakeSkip?.(); }
      else if (key.name === 'q') { state.quit = true; log('⏹  收到退出，正在收尾…'); wakeSkip?.(); wakePause?.(); }
    });
  }

  // 阻塞直到取消暂停（或退出）。
  async function waitIfPaused() {
    while (state.paused && !state.quit) {
      await new Promise(res => { wakePause = res; setTimeout(res, 500); });
    }
  }

  // 可打断的倒计时：s 跳过、q 退出会提前结束。带进度刷新。
  async function sleep(ms, label = '等待下一首') {
    state.skipWait = false;
    const end = Date.now() + ms;
    while (Date.now() < end && !state.quit && !state.skipWait) {
      const left = Math.ceil((end - Date.now()) / 1000);
      process.stdout.write(`\r⏳ ${label}：${left}s（s 跳过 / p 暂停 / q 退出）   `);
      await new Promise(res => { wakeSkip = res; setTimeout(res, 1000); });
    }
    process.stdout.write('\r' + ' '.repeat(60) + '\r');
  }

  function stop() {
    if (process.stdin.isTTY) { try { process.stdin.setRawMode(false); } catch {} process.stdin.pause(); }
  }

  return { state, waitIfPaused, sleep, stop };
}

export function log(...a) {
  const t = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  console.log(`[${t}]`, ...a);
}
