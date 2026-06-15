// 统一的解析结果结构，前端按这个结构渲染
function videoResult(o) {
  return {
    type: 'video',
    platform: o.platform || 'unknown',
    id: o.id || '',
    title: (o.title || '').trim(),
    url: o.url || '',
    cover: o.cover || '',
    author: o.author || '',
  };
}

function imageResult(o) {
  const images = (o.images || []).filter(Boolean);
  return {
    type: 'image',
    platform: o.platform || 'unknown',
    id: o.id || '',
    title: (o.title || '').trim(),
    images,
    cover: o.cover || images[0] || '',
    author: o.author || '',
  };
}

module.exports = { videoResult, imageResult };
