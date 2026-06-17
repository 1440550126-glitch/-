// utils/seccheck.js — 内容安全检测（封装 secCheck 云函数）
//
// 用法：
//   const seccheck = require('../../utils/seccheck.js');
//   if (!(await seccheck.checkText(v))) return;   // 不通过则中断
//
// 说明：
//   · 已开通云开发并部署 secCheck 云函数时，会调用微信内容安全接口校验。
//   · 未开通云开发（本地原型/开发者工具未登录云环境）时，默认放行，保证可正常体验。
//   · 文本为空直接放行。

function checkText(text) {
  return new Promise((resolve) => {
    const content = (text || '').trim();
    if (!content) return resolve(true);
    if (!wx.cloud || !wx.cloud.callFunction) return resolve(true); // 未启用云开发：放行
    wx.cloud.callFunction({
      name: 'secCheck',
      data: { type: 'text', text: content },
      success: (r) => {
        const pass = !(r && r.result && r.result.pass === false);
        if (!pass) wx.showToast({ title: '内容可能含违规信息，请修改后再试', icon: 'none' });
        resolve(pass);
      },
      fail: () => resolve(true) // 调用异常不阻断体验；如需更严格可改为 resolve(false)
    });
  });
}

module.exports = { checkText };
