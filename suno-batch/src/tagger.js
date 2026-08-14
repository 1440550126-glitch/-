// 自动打标签/归类：CSV 的 playlist 列留空时，按 曲风/情绪/主题 关键词把歌归到一个歌单类别。
// 纯规则、零依赖、可靠。命中不了就退回用 genre 本身，再不行归「未分类」。
// 想改分类口径直接改下面的 RULES 即可。

// 顺序 = 优先级：具体子流派在前，宽泛的「流行(pop)」兜底放最后
// （否则 "city pop" 会先被 "pop" 命中成「流行」）。
const RULES = [
  { name: '国风古风', kw: ['古风', '国风', '戏腔', 'guqin', 'guzheng', 'erhu', 'traditional chinese', '汉风', '民乐'] },
  { name: 'City Pop', kw: ['city pop', 'citypop', 'vaporwave', 'retro', '80s', '复古'] },
  { name: '二次元', kw: ['anime', 'j-pop', 'vocaloid', '二次元', '动漫'] },
  { name: '摇滚', kw: ['rock', 'metal', 'punk', 'grunge', '摇滚', 'band'] },
  { name: '说唱嘻哈', kw: ['rap', 'hip hop', 'hip-hop', 'trap', 'drill', '说唱', '嘻哈'] },
  { name: '电子', kw: ['edm', 'house', 'techno', 'synthwave', 'future bass', 'dubstep', 'trance', '电子', 'electronic'] },
  { name: '民谣', kw: ['folk', 'acoustic', 'singer-songwriter', '民谣', 'ballad'] },
  { name: 'R&B灵魂', kw: ['r&b', 'rnb', 'soul', 'neo-soul', 'funk', '节奏布鲁斯'] },
  { name: '爵士蓝调', kw: ['jazz', 'blues', 'swing', 'bossa', '爵士', '蓝调'] },
  { name: 'Lo-Fi放松', kw: ['lo-fi', 'lofi', 'chill', 'chillhop', 'study', '放松', '助眠'] },
  { name: '氛围器乐', kw: ['ambient', 'instrumental', 'cinematic', 'soundtrack', 'piano', 'meditation', '冥想', '轻音乐', '背景乐'] },
  { name: '流行', kw: ['pop', 'mandopop', 'cantopop', 'c-pop', '流行', 'dance pop', 'electropop'] },
];

const MOOD_RULES = [
  { name: '治愈暖心', kw: ['暖', '治愈', '温暖', 'warm', 'healing', 'cozy', 'gentle'] },
  { name: '悲伤情歌', kw: ['悲', '伤', '孤独', '难过', 'sad', 'melancholic', 'lonely', 'heartbreak'] },
  { name: '燃向热血', kw: ['燃', '热血', '励志', 'epic', 'powerful', 'energetic', 'hype', 'upbeat'] },
  { name: '浪漫甜蜜', kw: ['浪漫', '甜', '爱', 'romantic', 'sweet', 'love', 'dreamy'] },
];

function matchIn(rules, text) {
  const t = (text || '').toLowerCase();
  for (const r of rules) if (r.kw.some(k => t.includes(k.toLowerCase()))) return r.name;
  return null;
}

// 给一首歌定歌单：优先用户显式 playlist；否则按 曲风→情绪 关键词归类；再退回 genre；最后「未分类」。
export function classify(task, song = {}) {
  if (task.playlist && task.playlist.trim()) return task.playlist.trim();
  const genreText = `${task.genre} ${song.style || ''}`;
  const byGenre = matchIn(RULES, genreText);
  if (byGenre) return byGenre;
  const moodText = `${task.mood} ${task.theme} ${song.title || ''}`;
  const byMood = matchIn(MOOD_RULES, moodText);
  if (byMood) return byMood;
  const g = (task.genre || '').trim();
  return g ? g : '未分类';
}
