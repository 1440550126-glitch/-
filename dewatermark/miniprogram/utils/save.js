// 下载并保存到相册（视频 / 图片），自动处理相册授权
// 优先用云存储 fileID（域名自动在白名单内），否则回退到直链 downloadFile
function wxp(fn, opt) {
  return new Promise((resolve, reject) => fn({ ...opt, success: resolve, fail: reject }));
}

// 确保拿到「保存到相册」授权；被拒过则引导去设置页开启
function ensureAlbumAuth() {
  return wxp(wx.getSetting, {}).then((res) => {
    if (res.authSetting['scope.writePhotosAlbum'] === true) return true;
    if (res.authSetting['scope.writePhotosAlbum'] === false) {
      return wxp(wx.openSetting, {}).then((s) => {
        if (s.authSetting['scope.writePhotosAlbum']) return true;
        throw new Error('需要相册权限才能保存');
      });
    }
    return wxp(wx.authorize, { scope: 'scope.writePhotosAlbum' })
      .then(() => true)
      .catch(() => {
        throw new Error('需要相册权限才能保存');
      });
  });
}

// 把一个来源（fileID 或 url）下载成本地临时文件
function toTempFile(src) {
  if (src.fileID) {
    return wxp(wx.cloud.downloadFile, { fileID: src.fileID }).then((r) => r.tempFilePath);
  }
  return wxp(wx.downloadFile, { url: src.url }).then((r) => {
    if (r.statusCode !== 200) throw new Error('下载失败，链接可能已失效');
    return r.tempFilePath;
  });
}

function saveVideo(item) {
  const src = item.fileID ? { fileID: item.fileID } : { url: item.url };
  return ensureAlbumAuth()
    .then(() => toTempFile(src))
    .then((path) => wxp(wx.saveVideoToPhotosAlbum, { filePath: path }));
}

function saveImages(item) {
  const fileIDs = item.imageFileIDs || [];
  const urls = item.images || [];
  const sources = fileIDs.length ? fileIDs.map((f) => ({ fileID: f })) : urls.map((u) => ({ url: u }));
  return ensureAlbumAuth().then(async () => {
    let ok = 0;
    for (const src of sources) {
      try {
        const path = await toTempFile(src);
        await wxp(wx.saveImageToPhotosAlbum, { filePath: path });
        ok += 1;
      } catch (e) {
        // 跳过单张失败，继续保存其余
      }
    }
    if (!ok) throw new Error('图片保存失败');
    return ok;
  });
}

// 统一入口：根据素材类型保存
function saveMedia(item) {
  if (item.type === 'image' && ((item.images && item.images.length) || (item.imageFileIDs && item.imageFileIDs.length))) {
    return saveImages(item);
  }
  return saveVideo(item);
}

module.exports = { saveMedia, saveVideo, saveImages };
