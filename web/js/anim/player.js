// 全屏"文字变动画"播放器：长按帖子卡片触发
import { GET, POST } from '../api.js';
import { h, toast, aiBadge } from '../ui.js';
import { store, skinPayload } from '../store.js';
import { playManifest } from './engine.js';
import { nav } from '../router.js';

// ---- 提交即动效：发帖那一刻，文字立刻"活过来"飞出（纯客户端，零延迟、不耗配额） ----
const PATTERN_PARTICLE = { wind: 'windline', rain: 'raindrop', snow: 'snowflake', petal: 'petal', star: 'star', firefly: 'firefly', spark: 'spark', shard: 'shard', cloud: 'bubble' };
const PATTERN_AMBIENT = { rain: 'rain', wind: 'wind', star: 'night', firefly: 'night' };

// 从预览卡合成一份精简 manifest（情绪/调色板已在卡里，引擎补齐运动签名）
function synthFromCard(card = {}) {
  const dark = (card.bg && card.bg[0] && /^#[0-2]/.test(card.bg[0])) || false;
  return {
    v: 3, style: 'ink', seed: card.seed || Math.floor(Math.random() * 1e9),
    emotion: { key: card.emotion },
    palette: {
      bg: dark ? card.bg : ['#13101f', '#211b38'],     // 提交动效统一走深色舞台，辉光更"高级"
      ink: card.ink || '#ece9f7', accent: card.accent || '#9d8cff', glow: card.accent || '#7c6cff'
    },
    particles: [{ kind: PATTERN_PARTICLE[card.pattern] || 'star', density: 0.5 }],
    soundscape: { ambient: PATTERN_AMBIENT[card.pattern] || 'none', volume: 0.45 },
    behavior: { loop: false },
    timeline: [{ t: 0, action: 'glow', sound: 'chime' }, { t: 0.55, action: 'assemble', sound: 'swoosh' }, { t: 1.0, action: 'wake' }],
    text: { mode: 'particle_assemble', thickness: 1 }
  };
}

export function playSubmitAnim(content, card) {
  return new Promise((resolve) => {
    const overlays = document.getElementById('overlays');
    const cvs = h('canvas');
    const skip = h('button', { class: 'anim-skip' }, '跳过 ›');
    const overlay = h('div', { class: 'anim-overlay submit' },
      cvs,
      h('div', { class: 'anim-top' }, aiBadge('内容由 AI 辅助生成'), h('div', { style: { flex: 1 } }), skip),
      h('div', { class: 'anim-bottom' }, h('div', { class: 'anim-caption' }, '✨ 你的句子正在活过来'))
    );
    overlays.append(overlay);

    let engine = null, done = false;
    const finish = () => {
      if (done) return; done = true;
      engine?.stop();
      overlay.classList.add('fade-out');
      setTimeout(() => { overlay.remove(); resolve(); }, 360);
    };
    skip.addEventListener('click', finish);
    overlay.addEventListener('click', (e) => { if (e.target === overlay || e.target === cvs) finish(); });

    // 等一帧让画布拿到尺寸
    requestAnimationFrame(() => {
      engine = playManifest(cvs, synthFromCard(card), { text: content, submitMode: true, onDone: finish });
    });
    setTimeout(finish, 6000); // 兜底，绝不卡住发帖流程
  });
}

export async function openAnimPlayer(post) {
  let styles;
  try { styles = await GET('/api/ai/styles'); } catch (e) { toast(e.message, 'warn'); return; }

  const overlays = document.getElementById('overlays');
  const cvs = h('canvas');
  const caption = h('div', { class: 'anim-caption' });
  const chipsRow = h('div', { class: 'style-chips' });
  const quotaTip = h('div', { style: { textAlign: 'center', fontSize: '10.5px', color: 'rgba(255,255,255,.4)', marginTop: '10px' } });
  const muteBtn = h('button', { class: 'icon-btn', style: { background: 'rgba(255,255,255,.12)', border: 'none', color: '#fff' } }, '🔊');

  const overlay = h('div', { class: 'anim-overlay' },
    cvs,
    h('div', { class: 'anim-top' },
      aiBadge('内容由 AI 辅助生成'),
      h('span', { style: { color: 'rgba(255,255,255,.45)', fontSize: '11px' } }, `「${post.card?.emotion || ''}」`),
      h('div', { style: { flex: 1 } }),
      muteBtn
    ),
    h('button', { class: 'anim-close', style: { top: 'calc(60px + env(safe-area-inset-top, 0px))' } }, '✕'),
    h('div', { class: 'anim-bottom' }, caption, chipsRow, quotaTip)
  );

  let engine = null;
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    engine?.stop();
    overlay.remove();
  };
  overlay.querySelector('.anim-close').addEventListener('click', close);
  muteBtn.addEventListener('click', () => { muteBtn.textContent = engine?.toggleMute() ? '🔇' : '🔊'; });
  overlays.append(overlay);

  let counted = false;
  async function load(styleId) {
    try {
      const r = await POST(`/api/posts/${post.id}/manifest`, { style: styleId });
      engine?.stop();
      engine = playManifest(cvs, r.manifest, {
        text: post.content,
        fxPayload: skinPayload(store.me?.equipped?.anim_fx)
      });
      caption.textContent = r.manifest.caption || `${r.manifest.scene?.name || ''} · ${r.manifest.emotion?.key || ''}`;
      if (r.charged) toast(`已消耗 ${r.charged} 点星尘额度（余额 ${r.credits}）`);
      quotaTip.textContent = r.quota_left !== undefined
        ? (r.member ? `会员今日还可生成 ${r.quota_left} 次` : `今日免费体验还剩 ${r.quota_left} 次 · 开通会员解锁更多`)
        : '';
      if (!counted) { counted = true; POST(`/api/posts/${post.id}/play`).catch(() => {}); }
      renderChips(styleId);
      return true;
    } catch (e) {
      if (e.extra?.need_member) showMemberGate(e.message);
      else if (e.extra?.need_credits) showCreditGate(e);
      else toast(e.message, 'warn');
      return false;
    }
  }

  function renderChips(activeId) {
    chipsRow.innerHTML = '';
    for (const s of styles.styles) {
      const locked = s.tier === 'member' && !styles.member;
      const label = s.tier === 'premium' ? `${s.name} ✦${s.credit_cost}` : locked ? `${s.name} 🔒` : s.name;
      chipsRow.append(h('button', {
        class: `chip ${s.id === activeId ? 'active' : ''}`,
        onclick: async () => {
          if (s.id === activeId) return;
          if (s.tier === 'premium') {
            confirmPremium(s, () => load(s.id));
          } else {
            await load(s.id);
          }
        }
      }, label));
    }
  }

  function confirmPremium(s, go) {
    const ok = h('div', {
      style: {
        position: 'absolute', left: '50%', bottom: '120px', transform: 'translateX(-50%)', zIndex: 5,
        background: 'rgba(30,25,48,.95)', borderRadius: '18px', padding: '16px 18px', width: 'min(320px, 86vw)',
        color: '#fff', boxShadow: '0 14px 40px rgba(0,0,0,.5)'
      }
    },
      h('div', { style: { fontWeight: 700, marginBottom: '6px' } }, `${s.name} · 高级模型导演`),
      h('div', { style: { fontSize: '12px', color: 'rgba(255,255,255,.6)', lineHeight: 1.6, marginBottom: '12px' } },
        `${s.blurb}。预计消耗 ${s.credit_cost} 点星尘额度（当前余额 ${store.me?.credits ?? 0} 点）。`),
      h('div', { style: { display: 'flex', gap: '8px' } },
        h('button', { class: 'btn mini ghost', style: { flex: 1 }, onclick: () => ok.remove() }, '取消'),
        h('button', { class: 'btn mini', style: { flex: 1 }, onclick: () => { ok.remove(); go(); } }, '确认生成')
      )
    );
    overlay.append(ok);
  }

  function showMemberGate(msg) {
    caption.textContent = '';
    const gate = h('div', { style: { position: 'absolute', inset: 0, zIndex: 4, display: 'grid', placeItems: 'center', background: 'rgba(16,12,28,.82)' } },
      h('div', { style: { textAlign: 'center', padding: '0 36px' } },
        h('div', { style: { fontSize: '40px', marginBottom: '12px' } }, '🔮'),
        h('div', { style: { color: '#fff', fontWeight: 700, fontSize: '17px', marginBottom: '8px' } }, '让文字活过来'),
        h('div', { style: { color: 'rgba(255,255,255,.6)', fontSize: '13px', lineHeight: 1.7, marginBottom: '18px' } }, msg),
        h('button', { class: 'btn gold block', onclick: () => { close(); nav('/member'); } }, '9.9 元/月 开通会员'),
        h('button', { class: 'btn block ghost', style: { marginTop: '10px', background: 'rgba(255,255,255,.1)', color: '#fff' }, onclick: close }, '下次再说')
      )
    );
    overlay.append(gate);
  }

  function showCreditGate(e) {
    const gate = h('div', { style: { position: 'absolute', inset: 0, zIndex: 4, display: 'grid', placeItems: 'center', background: 'rgba(16,12,28,.82)' } },
      h('div', { style: { textAlign: 'center', padding: '0 36px' } },
        h('div', { style: { fontSize: '40px', marginBottom: '12px' } }, '✦'),
        h('div', { style: { color: '#fff', fontWeight: 700, fontSize: '16px', marginBottom: '8px' } }, '星尘额度不足'),
        h('div', { style: { color: 'rgba(255,255,255,.6)', fontSize: '13px', lineHeight: 1.7, marginBottom: '18px' } }, e.message),
        h('button', { class: 'btn block', onclick: () => { close(); nav('/member'); } }, '去补充额度'),
        h('button', { class: 'btn block ghost', style: { marginTop: '10px', background: 'rgba(255,255,255,.1)', color: '#fff' }, onclick: () => gate.remove() }, '换个基础风格')
      )
    );
    overlay.append(gate);
  }

  const okFirst = await load('ink');
  if (!okFirst && !overlay.querySelector('div[style*="z-index: 4"], div[style*="z-index:4"]')) {
    // 首次加载失败且没有引导层时，保留遮罩让用户看到提示
  }
}
