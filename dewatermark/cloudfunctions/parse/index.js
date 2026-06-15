const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

const parsers = require('./parsers');
const { tryThirdParty } = require('./lib/thirdparty');
const { downloadBuffer } = require('./lib/http');

// 是否把无水印视频转存到云存储后再返回（更稳，但产生存储/流量费用）。
// 在云函数环境变量里设置 PROXY_TO_STORAGE=1 开启。
const PROXY_TO_STORAGE = process.env.PROXY_TO_STORAGE === '1';

function extractUrl(text) {
  const m = String(text || '').match(/https?:\/\/[^\s，。、）)】\]"']+/i);
  return m ? m[0].replace(/[)）】\]]+$/, '') : '';
}

async function logParse(platform, via, type) {
  try {
    const { OPENID } = cloud.getWXContext();
    await db.collection('parse_logs').add({
      data: { openid: OPENID, platform, via, type, created_at: Date.now() },
    });
  } catch (e) {
    // 统计失败不影响主流程（集合不存在时忽略）
  }
}

exports.main = async (event) => {
  const text = String(event.text || event.url || '').trim();
  if (!text) return { ok: false, msg: '请粘贴分享链接' };

  const url = extractUrl(text);
  if (!url) return { ok: false, msg: '没找到有效链接，请复制完整的分享文案' };

  let result = null;
  let via = '';

  // 1) 内置平台解析
  try {
    result = await parsers.parse(url);
    via = 'builtin';
  } catch (e) {
    result = null;
  }

  // 2) 第三方聚合接口兜底（配置了才会触发）
  if (!result) {
    try {
      result = await tryThirdParty(url);
      if (result) via = 'thirdparty';
    } catch (e) {
      result = null;
    }
  }

  if (!result) {
    return { ok: false, msg: '解析失败，可能是链接失效或平台升级，请稍后再试' };
  }

  // 3) 可选：转存云存储（解决短视频 CDN 直链无法加入 downloadFile 白名单的问题）
  //    云存储域名 *.tcb.qcloud.la 自动在白名单内，保存更稳，但产生存储/流量费用。
  if (PROXY_TO_STORAGE) {
    const stamp = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    try {
      if (result.type === 'video' && result.url) {
        const buf = await downloadBuffer(result.url);
        const up = await cloud.uploadFile({ cloudPath: `videos/${stamp()}.mp4`, fileContent: buf });
        result.fileID = up.fileID;
      } else if (result.type === 'image' && Array.isArray(result.images) && result.images.length) {
        result.imageFileIDs = await Promise.all(
          result.images.map(async (u, i) => {
            const buf = await downloadBuffer(u);
            const up = await cloud.uploadFile({ cloudPath: `images/${stamp()}-${i}.jpg`, fileContent: buf });
            return up.fileID;
          })
        );
      }
    } catch (e) {
      // 转存失败则保留直链
    }
  }

  await logParse(result.platform, via, result.type);
  return { ok: true, via, data: result };
};
