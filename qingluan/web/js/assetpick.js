// 图片素材选择器（首帧/尾帧/参考图选择共用）
import { GET } from './api.js';
import { h, icon, modal } from './ui.js';

export async function openAssetPicker({ title = '选择图片素材', allowClear = true, onPick }) {
  const assets = (await GET('/api/assets')).filter((a) => a.kind === 'image');
  const grid = h('div', { class: 'asset-grid', style: { maxHeight: '54vh', overflowY: 'auto', paddingRight: '4px' } });
  const m = modal({
    title, wide: true, body: grid,
    actions: [
      ...(allowClear ? [{ label: '清除选择', onClick: () => onPick?.(null) }] : []),
      { label: '取消' }
    ]
  });
  if (!assets.length) {
    grid.append(h('div', { class: 'empty', style: { gridColumn: '1/-1' } },
      h('div', { html: icon('image', 32) }), h('p', {}, '资产库还没有图片：先用创作框「生成图片」或在画布上出图')));
    return;
  }
  for (const a of assets) {
    grid.append(h('div', { class: 'card asset-card', style: { cursor: 'pointer' }, onclick: () => { onPick?.(a); m.close(); } },
      h('div', { class: 'asset-thumb' }, h('img', { src: a.url, loading: 'lazy' })),
      h('div', { class: 'asset-meta' }, h('b', {}, a.name))));
  }
}
