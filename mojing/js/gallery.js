// 魔镜魔镜 · 本次会话相册（内存态）+ 保存/分享
// 媒体只存在内存与用户主动保存的文件里，刷新即清空，不落任何服务器。

export function createGallery() {
  const items = [];   // { id, kind:'photo'|'video', blob, url, time }

  function add(kind, blob) {
    const url = URL.createObjectURL(blob);
    const item = { id: 'm' + Date.now(), kind, blob, url, time: Date.now() };
    items.unshift(item);
    return item;
  }

  function extOf(blob, kind) {
    if (kind === 'photo') return 'jpg';
    if (blob.type.includes('mp4')) return 'mp4';
    return 'webm';
  }

  function fileName(item) {
    const d = new Date(item.time);
    const pad = (n) => String(n).padStart(2, '0');
    const stamp = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
    return `MagicMirror_${stamp}.${extOf(item.blob, item.kind)}`;
  }

  function download(item) {
    const a = document.createElement('a');
    a.href = item.url;
    a.download = fileName(item);
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  async function share(item) {
    const file = new File([item.blob], fileName(item), { type: item.blob.type });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({ files: [file], title: '魔镜魔镜', text: '我用魔镜魔镜拍的 ✨' });
        return true;
      } catch { /* 用户取消 */ return false; }
    }
    download(item);  // 不支持原生分享 → 退化为保存
    return false;
  }

  return {
    items,
    add, download, share, fileName,
    get latest() { return items[0] || null; },
    get count() { return items.length; }
  };
}
