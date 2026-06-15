// ============================================================
// 全局配置：上线前请把下面的占位值替换成你自己的真实值
// ============================================================
module.exports = {
  // 云开发环境 ID
  //   微信开发者工具 → 顶部「云开发」→ 设置 → 环境 ID
  cloudEnv: 'your-cloud-env-id',

  // 激励视频广告位 ID（变现核心：看完广告才解锁下载）
  //   mp.weixin.qq.com → 流量主 → 广告管理 → 新建「激励视频」广告位
  rewardedAdUnitId: 'adunit-xxxxxxxxxxxxxxxx',

  // Banner 广告位 ID（首页/结果页底部横幅）
  bannerAdUnitId: 'adunit-yyyyyyyyyyyyyyyy',

  // 插屏广告位 ID（解析成功时偶发弹出，可留空关闭）
  interstitialAdUnitId: '',

  // —— 业务策略（可按需调整）——
  // 是否必须看完激励视频才能下载（总开关，建议 true，这是广告收入主来源）
  requireAdToDownload: true,
  // 每日「免费」下载次数：仅在 quota 云函数不可用时的本地兜底值。
  //   新人免广告次数 / 分享得次数 / 每日免费数 的正式配置在 quota 云函数环境变量里：
  //   NEWBIE_FREE（新人初始，默认 3）/ SHARE_REWARD（每次分享 +，默认 2）/
  //   SHARE_DAILY_CAP（每日可奖励分享数，默认 3）/ DAILY_FREE（每日免费，默认 0）
  freeDownloadsPerDay: 0,
  // 客服/反馈邮箱（关于页展示）
  contactEmail: 'your@email.com',

  // 是否展示「内置解析仅供学习交流」的版权声明（过审建议保留 true）
  showCopyrightNotice: true,
};
