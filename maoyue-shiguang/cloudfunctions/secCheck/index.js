// cloudfunctions/secCheck/index.js — 内容安全检测云函数
// 调用微信「内容安全」开放接口，对用户输入的文本/图片做合规校验。
// 文本：security.msgSecCheck（v2）；图片：security.imgSecCheck。
//
// 部署：微信开发者工具右键本文件夹 →「上传并部署：云端安装依赖」。
// 依赖云开发已开通，且小程序具备「内容安全」接口权限（云函数 openapi 无需手动管理 access_token）。

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

exports.main = async (event) => {
  const { type = 'text', text = '', fileID = '' } = event || {};
  const { OPENID } = cloud.getWXContext();

  try {
    if (type === 'text') {
      const content = (text || '').trim();
      if (!content) return { pass: true, suggest: 'pass' };
      const res = await cloud.openapi.security.msgSecCheck({
        version: 2,
        scene: 2,            // 1资料 2评论 3论坛 4社交日志
        openid: OPENID,
        content
      });
      const suggest = res && res.result && res.result.suggest; // pass / review / risky
      return { pass: suggest === 'pass', suggest, label: res && res.result && res.result.label };
    }

    if (type === 'image' && fileID) {
      const dl = await cloud.downloadFile({ fileID });
      const res = await cloud.openapi.security.imgSecCheck({ media: { contentType: 'image/png', value: dl.fileContent } });
      return { pass: !!(res && res.errCode === 0) };
    }

    return { pass: true };
  } catch (e) {
    // 87014=内容含违规信息；其余多为环境/权限问题。文本默认按「不通过」处理，避免漏检。
    return { pass: false, error: (e && (e.errCode || e.message)) || String(e) };
  }
};
