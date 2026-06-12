// SRT 字幕生成：按分镜时长累计时间轴（可直接导入剪映 / CapCut / Premiere）
export function buildSRT(shots) {
  const pad = (n, w = 2) => String(n).padStart(w, '0');
  const fmt = (sec) => {
    const ms = Math.round((sec % 1) * 1000);
    const s = Math.floor(sec);
    return `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)},${pad(ms, 3)}`;
  };
  let t = 0;
  const blocks = [];
  shots.forEach((s, i) => {
    const dur = Math.max(1, Number(s.duration) || 5);
    const text = (s.dialogue || s.action || s.name || '').trim();
    if (text) blocks.push(`${blocks.length + 1}\n${fmt(t)} --> ${fmt(t + dur)}\n${text}`);
    t += dur;
  });
  return blocks.join('\n\n') + '\n';
}

export function downloadText(name, text, mime = 'text/plain') {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: `${mime};charset=utf-8` }));
  a.download = name;
  document.body.append(a);     // 入 DOM 才能保证下载文件名生效
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
