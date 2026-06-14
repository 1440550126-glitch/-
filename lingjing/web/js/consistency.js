// 画面一致性体检面板（项目页 / 画布页共用）
import { GET } from './api.js';
import { h, icon, modal, toast } from './ui.js';
import { runBatchGenerate } from './batch.js';

export async function openConsistency({ projectId, canvasId, onFixed }) {
  let report;
  try { report = await GET(`/api/projects/${projectId}/consistency`); }
  catch (e) { return toast(e.message, 'err'); }

  const body = h('div');
  const { close } = modal({ title: h('span', { html: `${icon('check')} 画面一致性体检` }), wide: true, body, actions: [] });

  function render(r) {
    body.innerHTML = '';
    const color = r.score >= 85 ? 'var(--ok)' : r.score >= 60 ? 'var(--warn)' : 'var(--err)';
    body.append(
      h('div', { style: { display: 'flex', gap: '18px', alignItems: 'center', marginBottom: '14px' } },
        h('div', { style: { width: '84px', height: '84px', borderRadius: '50%', flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', border: `5px solid ${color}`, font: '700 26px var(--font)', color } }, r.score),
        h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
          h('span', { class: 'pill teal' }, `角色定妆 ${r.stats.characters_ready}`),
          h('span', { class: 'pill teal' }, `场景图 ${r.stats.scenes_ready}`),
          h('span', { class: 'pill' }, `分镜首帧 ${r.stats.shots_framed}`),
          h('span', { class: 'pill' }, `风格：${String(r.stats.style).slice(0, 12)}`),
          h('span', { class: 'pill gold', title: '项目级生成种子：同项目所有出图共用，重生成更稳定' }, `种子 ${r.seed}`))),
      r.issues.length
        ? h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '42vh', overflowY: 'auto' } },
          r.issues.map((it) => h('div', { style: { padding: '10px 12px', borderRadius: '10px', background: it.level === 'err' ? 'var(--accent2-soft)' : 'var(--bg2)', fontSize: '13px' } },
            h('b', { style: { color: it.level === 'err' ? 'var(--err)' : 'var(--warn)' } }, it.level === 'err' ? '必须修复 · ' : '建议 · '),
            it.text,
            it.fix ? h('div', { style: { fontSize: '12px', color: 'var(--ink3)', marginTop: '2px' } }, `→ ${it.fix}`) : null)))
        : h('div', { class: 'empty' }, h('p', {}, '没有发现一致性风险，可以放心批量生成 ✓')),
      h('div', { class: 'm-actions' },
        h('button', { class: 'btn', onclick: () => close() }, '关闭'),
        h('button', { class: 'btn', title: '查看全片形象事实源：锁定档案 + 已生成定妆照/表情集', onclick: () => openCharacterProfile({ projectId }) }, h('span', { html: `${icon('user')} 角色记忆` })),
        h('button', {
          class: 'btn accent', onclick: (e) => {
            const b = e.currentTarget;
            b.disabled = true;
            close();
            runBatchGenerate(canvasId, {
              includeVideos: false,
              onDone: async () => {
                onFixed?.();
                openConsistency({ projectId, canvasId, onFixed });   // 修复后复检
              }
            });
          }
        }, '一键补齐缺失画面（先定妆照后首帧）')));
  }
  render(report);
}

// 角色记忆查看器：展示 character_profile.json（全片形象事实源），支持下载/复制
export async function openCharacterProfile({ projectId }) {
  let prof;
  try { prof = await GET(`/api/projects/${projectId}/character-profile`); }
  catch (e) { return toast(e.message, 'err'); }

  const thumb = (url, alt) => url
    ? h('img', { src: url, alt, style: { width: '52px', height: '64px', objectFit: 'cover', borderRadius: '8px', flex: 'none', border: '1px solid var(--line)' } })
    : h('div', { style: { width: '52px', height: '64px', borderRadius: '8px', flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg2)', color: 'var(--ink3)', fontSize: '11px', textAlign: 'center', border: '1px dashed var(--line)' } }, '未锁定');

  const charCard = (c) => h('div', { style: { display: 'flex', gap: '10px', padding: '10px', borderRadius: '10px', background: 'var(--bg2)' } },
    thumb(c.portrait, c.name),
    h('div', { style: { minWidth: 0, flex: 1 } },
      h('div', { style: { display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' } },
        h('b', {}, c.name),
        h('span', { class: 'pill teal' }, c.role),
        h('span', { class: 'pill' }, `${c.gender}·${c.age}`),
        c.ready ? h('span', { class: 'pill gold' }, '✓ 已锁定') : h('span', { class: 'pill', style: { color: 'var(--warn)' } }, '待生成定妆照')),
      h('div', { style: { fontSize: '12px', color: 'var(--ink2)', marginTop: '4px', lineHeight: 1.5 } }, c.lock || c.appearance),
      c.expressions?.length
        ? h('div', { style: { display: 'flex', gap: '4px', marginTop: '6px', flexWrap: 'wrap' } },
          c.expressions.map((e) => h('div', { style: { textAlign: 'center' } },
            h('img', { src: e.image, title: e.emotion, style: { width: '34px', height: '42px', objectFit: 'cover', borderRadius: '5px', border: '1px solid var(--line)' } }),
            h('div', { style: { fontSize: '10px', color: 'var(--ink3)' } }, e.emotion))))
        : null));

  const body = h('div', {},
    h('div', { style: { fontSize: '12px', color: 'var(--ink3)', marginBottom: '8px' } }, prof.note),
    h('details', { style: { marginBottom: '10px' } },
      h('summary', { style: { cursor: 'pointer', fontWeight: 600 } }, '总控提示词（写进每张参考图）'),
      h('div', { style: { fontSize: '12px', color: 'var(--ink2)', margin: '6px 0', lineHeight: 1.6 } }, prof.master_control),
      h('div', { style: { fontSize: '12px', color: 'var(--err)', lineHeight: 1.6 } }, `禁止项：${(prof.forbidden_rules || []).join('；')}`)),
    h('div', { style: { display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '50vh', overflowY: 'auto' } },
      h('div', { style: { fontWeight: 600, fontSize: '13px' } }, `角色（${prof.characters.length}）`),
      ...prof.characters.map(charCard),
      prof.scenes?.length ? h('div', { style: { fontWeight: 600, fontSize: '13px', marginTop: '6px' } }, `场景（${prof.scenes.length}）`) : null,
      ...(prof.scenes || []).map((s) => h('div', { style: { display: 'flex', gap: '10px', padding: '8px 10px', borderRadius: '10px', background: 'var(--bg2)', fontSize: '12px' } },
        thumb(s.image, s.name), h('div', { style: { flex: 1 } }, h('b', {}, s.name), s.ready ? h('span', { class: 'pill gold', style: { marginLeft: '6px' } }, '✓') : null, h('div', { style: { color: 'var(--ink2)', marginTop: '3px' } }, s.lock || s.desc)))),
      prof.props?.length ? h('div', { style: { fontWeight: 600, fontSize: '13px', marginTop: '6px' } }, `道具（${prof.props.length}）`) : null,
      ...(prof.props || []).map((p) => h('div', { style: { padding: '6px 10px', borderRadius: '8px', background: 'var(--bg2)', fontSize: '12px' } }, h('b', {}, p.name), '：', p.lock || p.desc))),
    h('div', { class: 'm-actions' },
      h('button', { class: 'btn', onclick: () => navigator.clipboard?.writeText(JSON.stringify(prof, null, 2)).then(() => toast('已复制 character_profile.json', 'ok')) }, h('span', { html: `${icon('copy')} 复制 JSON` })),
      h('button', {
        class: 'btn accent', onclick: () => {
          const blob = new Blob([JSON.stringify(prof, null, 2)], { type: 'application/json' });
          const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: `character_profile-${prof.project.title || projectId}.json` });
          a.click(); URL.revokeObjectURL(a.href); toast('已下载 character_profile.json', 'ok');
        }
      }, h('span', { html: `${icon('download')} 下载 character_profile.json` }))));

  modal({ title: h('span', { html: `${icon('user')} 角色记忆 · character_profile.json` }), wide: true, body });
}
