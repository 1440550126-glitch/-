const BLOCK_KEYWORDS = ['约炮', '裸聊', '赌博', '博彩', '代购违禁', '买粉', '诈骗', '血腥'];
const RISK_KEYWORDS = ['自杀', '轻生', '不想活', '割腕', '跳楼', '伤害自己'];
function moderateText(text) {
  const content = String(text || '').trim();
  const hitBlock = BLOCK_KEYWORDS.find((word) => content.includes(word));
  if (hitBlock) return { status: 'blocked', reason: `命中禁止内容：${hitBlock}`, visible: false };
  const hitRisk = RISK_KEYWORDS.find((word) => content.includes(word));
  if (hitRisk) return { status: 'review', reason: '疑似自伤/轻生表达，将降低扩散并提示求助。', visible: false, care: true };
  if (!content) return { status: 'blocked', reason: '内容不能为空', visible: false };
  return { status: 'safe', reason: '通过关键词与模拟 AI 审核', visible: true };
}
module.exports = { moderateText, BLOCK_KEYWORDS, RISK_KEYWORDS };
