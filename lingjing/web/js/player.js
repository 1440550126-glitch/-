// 灵境AI · 放映室：按分镜顺序连播预览成片效果（mp4 用 video，本地 SVG 预览用 img + 计时）
import { POST } from './api.js';
import { h, icon, toast, isVideoUrl } from './ui.js';
import { buildSRT, downloadText } from './srt.js';

/**
 * @param {{title:string, projectId:string, groups:Array<{key:string,label:string,shots:Array<{order,name,url,poster,dialogue,action,duration,shot_type,camera}>}>, startGroup?:string}} opts
 */
export function openScreeningRoom({ title, projectId = '', groups, startGroup = '' }) {
  let group = groups.find((g) => g.key === startGroup) || groups[0];
  let idx = 0;
  let playing = true;
  let timer = null;          // 本地 SVG 片段的推进计时
  let remain = 0;
  let tickStart = 0;

  const stage = h('div', { class: 'sr-stage' });
  const sub = h('div', { class: 'sr-sub' });
  const counter = h('span', { class: 'sr-counter' });
  const playBtn = h('button', { class: 'btn sm', onclick: () => toggle() });

  // 镜头分析侧栏（镜号/景别/运镜/画面/分析），随播放高亮当前镜，可点行跳转
  const analysis = h('div', { class: 'sr-analysis' });
  let rowEls = [];
  function buildAnalysis() {
    analysis.innerHTML = '';
    analysis.append(h('div', { class: 'sr-an-head' },
      h('span', { style: { width: '34px' } }, '镜号'), h('span', { style: { width: '40px' } }, '景别'),
      h('span', { style: { width: '40px' } }, '运镜'), h('span', { class: 'grow' }, '镜头分析')));
    rowEls = group.shots.map((s, i) => {
      const thumb = s.poster || (isVideoUrl(s.url) ? '' : s.url);
      const row = h('div', { class: 'sr-an-row', onclick: () => go(i) },
        h('span', { class: 'sr-an-no', style: { width: '34px' } }, String(s.order).padStart(2, '0')),
        h('span', { style: { width: '40px' } }, s.shot_type || '—'),
        h('span', { style: { width: '40px' } }, s.camera || '—'),
        h('div', { class: 'sr-an-desc' },
          thumb ? h('img', { class: 'sr-an-thumb', src: thumb, loading: 'lazy' }) : null,
          h('span', {}, s.action || s.dialogue || s.name)));
      return row;
    });
    analysis.append(...rowEls);
  }
  function highlightRow() {
    rowEls.forEach((r, i) => r.classList.toggle('on', i === idx));
    rowEls[idx]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  // 台词朗读（浏览器语音合成，零依赖配音预览）
  let speakOn = false;
  const canSpeak = 'speechSynthesis' in window;
  const voiceBtn = h('button', {
    class: 'btn sm', title: canSpeak ? '台词朗读（系统语音配音预览）' : '当前浏览器不支持语音合成', disabled: !canSpeak,
    onclick: () => {
      speakOn = !speakOn;
      voiceBtn.style.background = speakOn ? 'var(--accent)' : '';
      speechSynthesis.cancel();
      if (speakOn) speakLine();
    }
  }, '🔊 朗读');
  // 配音文件优先（火山 TTS 生成的 mp3 随分镜同步播放），浏览器朗读作兜底
  let curAudio = null;
  function stopAudio() {
    if (curAudio) { curAudio.pause(); curAudio = null; }
  }
  function playDub(s) {
    stopAudio();
    if (!s?.audio) return false;
    curAudio = new Audio(s.audio);
    curAudio.play().catch(() => { /* 自动播放被拦截时忽略 */ });
    return true;
  }
  function speakLine() {
    if (!canSpeak) return;
    speechSynthesis.cancel();
    const s = group.shots[idx];
    if (s?.audio || !speakOn) return;   // 有配音文件则不用浏览器朗读
    if (!s?.dialogue) return;
    const u = new SpeechSynthesisUtterance(s.dialogue);
    u.lang = 'zh-CN';
    u.rate = 1.05;
    const zh = speechSynthesis.getVoices().find((v) => /zh|Chinese/i.test(v.lang));
    if (zh) u.voice = zh;
    speechSynthesis.speak(u);
  }

  const groupSel = h('select', { class: 'select', style: { width: 'auto' }, onchange: (e) => {
    group = groups.find((g) => g.key === e.target.value) || groups[0];
    idx = 0;
    buildAnalysis();
    renderShot();
  } }, groups.map((g) => h('option', { value: g.key, selected: g.key === group.key }, `${g.label}（${g.shots.length} 镜）`)));

  const exportBtn = h('button', { class: 'btn sm', onclick: async () => {
    if (!projectId) return;
    exportBtn.disabled = true;
    exportBtn.innerHTML = `${icon('loader')} 导出中…`;
    try {
      const r = await POST(`/api/projects/${projectId}/export`, { episode: group.key === 'all' ? '' : group.key });
      toast(`成片已导出（${r.shots} 镜拼接），已存入资产库`, 'ok');
      open(r.url, '_blank');
    } catch (e) { toast(e.message, 'err'); }
    exportBtn.disabled = false;
    exportBtn.innerHTML = `${icon('download', 15)} 导出 MP4`;
  } });
  exportBtn.innerHTML = `${icon('download', 15)} 导出 MP4`;

  const analysisBtn = h('button', { class: 'btn sm', title: '镜头分析表（边看边对照每一镜，可点行跳转）', onclick: () => {
    const on = room.classList.toggle('sr-show-analysis');
    analysisBtn.style.background = on ? 'var(--accent)' : '';
    if (on) highlightRow();
  } }, '🎞 镜头分析');
  const room = h('div', { class: 'screen-room sr-show-analysis' },
    h('div', { class: 'sr-top' },
      h('b', {}, `放映室 · ${title}`), groupSel, h('span', { class: 'grow' }),
      h('button', { class: 'btn sm', title: '导出当前分组的 SRT 字幕（可导入剪映/CapCut）', onclick: () => {
        downloadText(`${title}-${group.label}.srt`, buildSRT(group.shots));
        toast('SRT 字幕已导出', 'ok');
      } }, '字幕'),
      analysisBtn,
      voiceBtn,
      projectId ? exportBtn : null,
      h('button', { class: 'btn sm', html: icon('x', 15), title: '关闭 (Esc)', onclick: () => close() })),
    h('div', { class: 'sr-body' },
      h('div', { class: 'sr-viewer' },
        stage, sub,
        h('div', { class: 'sr-controls' },
          h('button', { class: 'btn sm', html: icon('back', 15), title: '上一镜 (←)', onclick: () => go(idx - 1) }),
          playBtn,
          h('button', { class: 'btn sm', style: { transform: 'scaleX(-1)' }, html: icon('back', 15), title: '下一镜 (→)', onclick: () => go(idx + 1) }),
          counter)),
      analysis));
  analysisBtn.style.background = 'var(--accent)';

  function clearTimer() { clearTimeout(timer); timer = null; }
  function go(i) {
    if (!group.shots.length) return;
    idx = (i + group.shots.length) % group.shots.length;
    renderShot();
  }
  function next() { go(idx + 1); }
  function toggle() {
    playing = !playing;
    playBtn.innerHTML = icon(playing ? 'x' : 'play', 15);
    playBtn.title = playing ? '暂停 (空格)' : '播放 (空格)';
    const v = stage.querySelector('video');
    if (v) playing ? v.play() : v.pause();
    else if (playing) { tickStart = Date.now(); timer = setTimeout(next, remain); }
    else { clearTimer(); remain -= Date.now() - tickStart; }
    playBtn.innerHTML = playing ? '⏸' : `▶`;
  }

  function renderShot() {
    clearTimer();
    stage.innerHTML = '';
    const s = group.shots[idx];
    playDub(s);
    speakLine();
    highlightRow();
    counter.textContent = `SHOT ${String(s.order).padStart(2, '0')} · ${idx + 1}/${group.shots.length}`;
    sub.innerHTML = '';
    if (s.dialogue) sub.append(h('span', { class: 'sr-line' }, `「${s.dialogue}」`));
    else if (s.action) sub.append(h('span', { class: 'sr-line dim' }, s.action));
    if (!s.url) {
      stage.append(h('div', { class: 'sr-empty' }, h('span', { html: icon('film', 34) }), h('p', {}, `${s.name} 还没有生成视频/首帧`)));
      remain = 1800;
      if (playing) { tickStart = Date.now(); timer = setTimeout(next, remain); }
      return;
    }
    if (isVideoUrl(s.url)) {
      const v = h('video', { src: s.url, autoplay: playing, playsinline: true, poster: s.poster || undefined });
      v.addEventListener('ended', () => playing && next());
      stage.append(v);
    } else {
      stage.append(h('img', { src: s.url }));
      remain = Math.max(1500, (s.duration || 5) * 1000);
      if (playing) { tickStart = Date.now(); timer = setTimeout(next, remain); }
    }
    playBtn.innerHTML = playing ? '⏸' : '▶';
    playBtn.title = '播放/暂停 (空格)';
  }

  const onKey = (e) => {
    if (e.key === 'Escape') return close();
    if (e.key === 'ArrowRight') return go(idx + 1);
    if (e.key === 'ArrowLeft') return go(idx - 1);
    if (e.key === ' ') { e.preventDefault(); toggle(); }
  };
  function close() {
    clearTimer();
    stopAudio();
    if (canSpeak) speechSynthesis.cancel();
    document.removeEventListener('keydown', onKey);
    room.remove();
  }
  document.addEventListener('keydown', onKey);
  document.body.append(room);
  buildAnalysis();
  renderShot();
  return { close };
}
