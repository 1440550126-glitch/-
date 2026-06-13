// 灵境AI · 风格库：预设画面风格（对标小云雀风格库，注入到生图/生视频提示词）
// project.style 存「风格名」或自定义提示词原文；resolveStylePrompt 负责换算成完整提示词。

export const STYLE_CATS = [
  { id: 'film', name: '电影感' },
  { id: 'real', name: '真人' },
  { id: 'd2', name: '2D' },
  { id: 'd3', name: '3D' }
];

export const STYLES = [
  // —— 电影感 ——
  { id: 'hollywood-retro', cat: 'film', name: '美式复古好莱坞', prompt: '美式复古好莱坞电影风格，35mm胶片颗粒，琥珀金色调，高对比戏剧布光，浅景深，黄金年代质感' },
  { id: 'orange-teal', cat: 'film', name: '橙青电影色调', prompt: '现代商业大片风格，橙青对比色调（teal & orange），电影宽幅构图，锐利细节，高动态范围' },
  { id: 'hk-90s', cat: 'film', name: '90年代港片', prompt: '90年代香港电影风格，霓虹灯光，潮湿街道反光，胶片噪点，暖黄与霓虹蓝绿交织，王家卫式抽帧氛围' },
  { id: 'neon-cyber', cat: 'film', name: '霓虹赛博电影', prompt: '赛博朋克电影风格，霓虹紫蓝色调，雨夜都市，全息广告光污染，高对比暗调，未来感镜头光晕' },
  { id: 'suspense-cold', cat: 'film', name: '悬疑冷调', prompt: '悬疑惊悚电影风格，冷峻青灰色调，低照度硬光，阴影占比大，压迫感构图，雾气与逆光剪影' },
  { id: 'war-retro', cat: 'film', name: '复古战争电影', prompt: '复古战争史诗电影风格，做旧褪色胶片，烟尘弥漫，土黄与铁灰色调，手持镜头颗粒感' },
  { id: 'wuxia-real', cat: 'film', name: '武侠江湖写实', prompt: '武侠电影写实摄影风格，水墨般留白构图，竹林雾气，冷月青衫，自然光影，刀剑寒光质感' },
  { id: 'cn-warm-blue', cat: 'film', name: '中式暖调蓝辉', prompt: '中式都市电影风格，室内暖黄钨丝灯与窗外冷蓝夜色对比，烟火气，写实生活质感' },

  // —— 真人 ——
  { id: 'kr-soft', cat: 'real', name: '韩剧都市柔光', prompt: '韩剧都市偶像剧风格，柔光滤镜，奶油肤色调，大光圈浅景深，干净通透的现代都市质感' },
  { id: 'jp-youth', cat: 'real', name: '日式青春胶片', prompt: '日系青春电影胶片风格，过曝白皙，低饱和蓝绿色调，夏日光斑，清新通透空气感' },
  { id: 'cn-city-real', cat: 'real', name: '国产都市写实', prompt: '国产都市剧写实风格，自然光，真实肤质，生活化场景细节，纪实感构图' },
  { id: 'palace-cold', cat: 'real', name: '宫斗权谋冷峻', prompt: '古装宫斗剧风格，深宫红墙金瓦，冷峻低饱和色调，烛光侧逆光，华服细节，权谋压迫氛围' },
  { id: 'guou-soft', cat: 'real', name: '古偶唯美柔光', prompt: '古装偶像剧唯美风格，柔焦仙气，飘逸纱衣，桃花柳絮，粉金柔光，梦幻浅景深' },
  { id: 'kr-minimal', cat: 'real', name: '韩国冷淡电影', prompt: '韩国独立电影冷淡风，低饱和灰绿色调，留白构图，阴天漫射光，疏离孤独氛围' },
  { id: 'countryside-90s', cat: 'real', name: '90年代乡土叙事', prompt: '90年代中国农村电影风格，土黄暖调，麦田与土路，自然顶光，朴素写实，年代感服化道' },

  // —— 2D ——
  { id: 'hot-blood-anime', cat: 'd2', name: '高质量热血漫', prompt: '高质量2D热血动漫风格，强烈速度线，张力构图，鲜明赛璐璐上色，锐利高光，战斗气场特效' },
  { id: 'otomo', cat: 'd2', name: '大友克洋风', prompt: '大友克洋风格2D动画，精密机械与都市废墟细节，冷灰色调，写实人物比例，80年代日本科幻漫画质感' },
  { id: 'ink-guofeng', cat: 'd2', name: '东方水墨', prompt: '中国水墨画风格，写意笔触，墨色浓淡干湿，留白意境，朱砂点缀，宣纸纹理' },
  { id: 'retro-manhua', cat: 'd2', name: '中国神话连环画', prompt: '中国古典连环画风格，工笔线描，矿物颜料平涂，敦煌配色，神话人物造型，复古印刷质感' },
  { id: 'dark-concept', cat: 'd2', name: '黑暗原画概念', prompt: '黑暗奇幻概念原画风格，厚涂笔触，低明度高对比，体积光，史诗感构图，细节丰富的环境叙事' },
  { id: 'kids-crayon', cat: 'd2', name: '儿童蜡笔手绘', prompt: '儿童蜡笔手绘插画风格，稚拙笔触，高饱和明快配色，纸面纹理，温暖童趣' },
  { id: 'bw-manga', cat: 'd2', name: '黑白二维漫画', prompt: '黑白漫画风格，网点纸阴影，粗细变化的钢笔线条，强对比分镜感，日式漫画排线' },
  { id: 'retro-psyche', cat: 'd2', name: '复古肌理迷幻插画', prompt: '复古迷幻插画风格，丝网印刷肌理，撞色渐变，流动曲线构图，70年代海报质感' },

  // —— 3D ——
  { id: 'pixar', cat: 'd3', name: '皮克斯卡通渲染', prompt: '皮克斯风格3D卡通渲染，圆润造型，次表面散射皮肤，柔和全局光照，高细节材质，温暖色调' },
  { id: 'ue5-real', cat: 'd3', name: 'UE5写实渲染', prompt: 'UE5虚幻引擎写实渲染，电影级光线追踪，PBR材质，真实景深与运动模糊，8K细节' },
  { id: 'clay-stop', cat: 'd3', name: '粘土定格动画', prompt: '粘土定格动画风格，手工捏制质感，指纹与瑕疵细节，微缩布景，棚拍柔光，阿德曼工作室质感' },
  { id: 'cn-fantasy-3d', cat: 'd3', name: '国风3D奇幻', prompt: '中国奇幻3D动画风格，国风建筑与服饰，仙侠粒子特效，青绿山水配色，电影级渲染' },
  { id: 'soul-dark-3d', cat: 'd3', name: '魂系黑暗渲染', prompt: '魂系游戏3D渲染风格，哥特废墟，阴郁体积雾，冷灰金属与火光对比，史诗压迫感' },
  { id: 'jelly-y2k', cat: 'd3', name: '复古Y2K梦幻', prompt: 'Y2K千禧年3D风格，果冻半透明塑料材质，镭射渐变，光泽高光，梦幻粉紫蓝配色' },
  { id: 'game-concept', cat: 'd3', name: '游戏概念艺术', prompt: '3A游戏概念艺术风格，宏大场景设定图，体积光与大气透视，写实材质，战斗场面张力' }
];

const byName = new Map(STYLES.map((s) => [s.name, s]));

/** 「风格名 / 自定义提示词 / 空」→ 注入用的完整提示词 */
export function resolveStylePrompt(style = '') {
  const s = String(style || '').trim();
  if (!s) return '';
  return byName.get(s)?.prompt || s;
}
