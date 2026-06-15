// 一句话变一首歌：拉取 Song Manifest → Web Audio "演唱" + 歌词逐字点亮
import { POST } from '../api.js';
import { h, toast, aiBadge } from '../ui.js';
import { SoundScape } from './sound.js';
import { nav } from '../router.js';

const MODE_CN = { major: '大调', minor: '小调', pentatonic_major: '五声·宫', pentatonic_minor: '五声·羽' };

export async function openSongPlayer(post) {
  const overlays = document.getElementById('overlays');
  let data;
  try {
    data = await POST(`/api/posts/${post.id}/song`);
  } catch (e) {
    if (e.extra?.need_member) return showSongGate(overlays, e.message);
    toast(e.message || '生成失败，稍后再试', 'warn');
    return;
  }
  const song = data.song;

  // 歌词逐字（按旋律音符顺序）
  const lyricWrap = h('div', { class: 'song-lyric' });
  const chars = (song.melody || []).map((nt) => {
    const span = h('span', { class: 'song-ch' }, nt.lyric || '');
    lyricWrap.append(span);
    return span;
  });
  if (!chars.length) lyricWrap.textContent = song.lyric || '';

  const playBtn = h('button', { class: 'btn block gold', style: { flex: '1' } }, '▶ 播放');
  const muteBtn = h('button', { class: 'icon-btn' }, '🔊');

  const card = h('div', { class: 'song-card glass' },
    h('div', { class: 'song-top' },
      aiBadge(song.meta?.ai_label || 'AI 生成旋律'),
      h('div', { style: { flex: 1 } }),
      h('button', { class: 'song-x', onclick: () => close() }, '✕')
    ),
    h('div', { class: 'song-title' }, `♫ ${song.title || '无题'}`),
    h('div', { class: 'song-meta' },
      `${song.keyName} ${MODE_CN[song.mode] || ''} · ${song.bpm} BPM · 「${song.emotion?.key || ''}」`),
    lyricWrap,
    h('div', { class: 'song-controls' }, playBtn, muteBtn)
  );
  const overlay = h('div', { class: 'song-overlay' }, card);

  let sound = null;
  let playing = false;
  let closed = false;

  function close() {
    if (closed) return;
    closed = true;
    sound?.stop();
    overlay.remove();
  }
  function reset() { chars.forEach((c) => c.classList.remove('on')); }

  function play() {
    sound?.stop();
    reset();
    try { sound = new SoundScape(); sound.setVolume(0.7); }
    catch { toast('当前环境不支持音频播放', 'warn'); return; }
    playing = true;
    playBtn.textContent = '◼ 停止';
    muteBtn.textContent = '🔊';
    sound.playMelody(song, {
      onNote: (_n, i) => { chars[i]?.classList.add('on'); },
      onEnd: () => { playing = false; playBtn.textContent = '↻ 再唱一次'; }
    });
  }

  playBtn.addEventListener('click', () => {
    if (playing) { sound?.stop(); playing = false; playBtn.textContent = '▶ 播放'; }
    else play();
  });
  muteBtn.addEventListener('click', () => { muteBtn.textContent = sound?.toggleMute() ? '🔇' : '🔊'; });
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

  overlays.append(overlay);
  if (data.quota_left !== undefined) {
    toast(data.member ? `会员今日还可生成 ${data.quota_left} 首` : `今日免费旋律还剩 ${data.quota_left} 首`);
  }
  play(); // 由按钮点击的手势触发，自动唱一次
}

function showSongGate(overlays, msg) {
  const overlay = h('div', { class: 'song-overlay' },
    h('div', { class: 'song-card glass', style: { textAlign: 'center' } },
      h('div', { style: { fontSize: '40px', marginBottom: '10px' } }, '🎵'),
      h('div', { style: { fontWeight: 700, fontSize: '17px', marginBottom: '8px' } }, '让这句话唱出来'),
      h('div', { style: { fontSize: '13px', color: 'var(--ink-soft, #8a85a0)', lineHeight: 1.7, marginBottom: '18px' } }, msg),
      h('button', { class: 'btn gold block', onclick: () => { overlay.remove(); nav('/member'); } }, '9.9 元/月 开通会员'),
      h('button', { class: 'btn block ghost', style: { marginTop: '10px' }, onclick: () => overlay.remove() }, '下次再说')
    )
  );
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  overlays.append(overlay);
}
