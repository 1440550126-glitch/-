// 商业化目录：会员方案 / 高级额度包 / 预置头像（按月订阅，低于市场、非廉价）
// 两档：自带Key版（便宜，平台只做编排、模型自带不限量）/ 省心版（贵，含平台模型、开箱即用）。
export const MEMBER_PLANS = [
  { id: 'm1', name: '自带Key版 · 月卡', months: 1, price_fen: 3900, llm_tier: 'byok', blurb: '平台编排 + 自带模型 Key，不限量跑' },
  { id: 'p1', name: '省心版 · 月卡', months: 1, price_fen: 9900, llm_tier: 'easy', blurb: '含平台模型，免配置开箱即用（80 次/天）', tag: '推荐' }
];

export const MEMBER_BENEFITS = [
  '解锁「文字变动画」无限播放（每日防刷上限内）',
  '解锁樱粉 / 霓夜 / 星海 3 种基础动画风格与音效',
  '解锁更多预览卡模板',
  '每日基础 AI 生成次数提升至 100 次',
  '高级动画风格 8 折消耗额度',
  '会员专属「流星环」头像框',
  'AI 暖场官优先互动'
];

export const CREDIT_PACKS = [
  { id: 'c60', name: '星尘额度 ×60', credits: 60, price_fen: 600, blurb: '约可生成 6 次高级风格动画' },
  { id: 'c200', name: '星河额度 ×200', credits: 200, price_fen: 1800, blurb: '约可生成 20 次以上', tag: '更划算' }
];

// 配额与计价（后台 settings 可覆盖）
export const QUOTA = {
  FREE_ANIM_PER_DAY: 3,        // 免费用户每日"文字变动画"体验次数
  MEMBER_ANIM_PER_DAY: 100,    // 会员每日上限（防刷）
  PREMIUM_CREDIT_COST: 10,     // 高级风格每次消耗额度
  MEMBER_PREMIUM_COST: 8,      // 会员折扣价
  POST_PER_DAY: 30,            // 每日发帖上限（防刷）
  COMMENT_PER_DAY: 200
};

// 预置可爱头像（客户端用渐变 + 表情渲染，无外部资源）
export const AVATARS = [
  { id: 'blob_1', name: '软糖糯米', colors: ['#ffd6e8', '#ff9ec6'], face: '˶ᵔ ᵕ ᵔ˶' },
  { id: 'blob_2', name: '云朵团子', colors: ['#dbeafe', '#93c5fd'], face: '￫ ‿ ￩' },
  { id: 'blob_3', name: '抹茶麻薯', colors: ['#dcfce7', '#86efac'], face: '> ᴗ <' },
  { id: 'blob_4', name: '香芋啵啵', colors: ['#ede9fe', '#c4b5fd'], face: 'ᴗ ﹏ ᴗ' },
  { id: 'blob_5', name: '柠檬汽水', colors: ['#fef9c3', '#fde047'], face: '◕ ‿ ◕' },
  { id: 'blob_6', name: '蜜桃乌龙', colors: ['#ffe4e6', '#fda4af'], face: '˘ ³˘' },
  { id: 'blob_7', name: '海盐苏打', colors: ['#cffafe', '#67e8f9'], face: 'o ᴗ o' },
  { id: 'blob_8', name: '星空慕斯', colors: ['#e0e7ff', '#818cf8'], face: '✧ ᴗ ✧' },
  { id: 'blob_9', name: '焦糖布丁', colors: ['#fef3c7', '#fbbf24'], face: 'ᵔ ⤙ ᵔ' },
  { id: 'blob_10', name: '黑芝麻汤圆', colors: ['#e5e7eb', '#9ca3af'], face: '– ᴗ –' },
  { id: 'blob_11', name: '樱花气泡', colors: ['#fce7f3', '#f9a8d4'], face: '๑ ᴗ ๑' },
  { id: 'blob_12', name: '薄荷冰沙', colors: ['#d1fae5', '#6ee7b7'], face: '≧ ᴗ ≦' }
];

export const REPORT_REASONS = ['色情低俗', '暴力血腥', '赌博诈骗', '攻击辱骂', '违法信息', '引导私下交易', '不适合未成年人', '自伤自残风险', '其他'];
