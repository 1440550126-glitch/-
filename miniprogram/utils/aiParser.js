const EMOTION_RULES = [
  { key: '孤独', words: ['孤独', '一个人', '原地', '等', '夜', '想你', '失眠', '空'], color: ['#1B1D2A', '#596175'] },
  { key: '恋爱', words: ['爱', '喜欢', '你', '心动', '拥抱', '见你', '牵手'], color: ['#FFE5EC', '#FFD1DC'] },
  { key: '治愈', words: ['风', '太阳', '慢慢', '温柔', '云', '猫', '花', '好好'], color: ['#F6F3EE', '#DDE7F0'] },
  { key: '搞笑', words: ['哈哈', '离谱', '摔', '笑', '猫', '打工', '脑袋'], color: ['#FFF4B8', '#FFD6A5'] },
  { key: '热血', words: ['冲', '奔跑', '赢', '燃', '热烈', '少年', '出发'], color: ['#FFE0C2', '#FF6B4A'] },
  { key: 'emo', words: ['破防', '碎', '哭', '雨', '算了', '难过'], color: ['#20212D', '#4D566E'] }
];

const OBJECT_RULES = [
  { words: ['风', '吹'], object: 'wind_1', type: 'wind_line', action: 'move_left_to_right', sound: 'wind_soft' },
  { words: ['雨', '下雨', '雨停'], object: 'rain_1', type: 'rain', action: 'rain_fall_to_stop', sound: 'rain_soft' },
  { words: ['雪'], object: 'snow_1', type: 'snow', action: 'snow_fall', sound: 'wind_soft' },
  { words: ['海', '浪'], object: 'wave_1', type: 'wave', action: 'wave_push', sound: 'ocean_soft' },
  { words: ['云'], object: 'cloud_1', type: 'cloud', action: 'cloud_float', sound: 'wind_soft' },
  { words: ['猫'], object: 'cat_1', type: 'cat', action: 'cat_jump_in', sound: 'cat_meow_soft' },
  { words: ['心', '心动'], object: 'heart_1', type: 'heart_line', action: 'heartbeat_once', sound: 'heartbeat_soft' },
  { words: ['碎', '心碎', '破防'], object: 'broken_heart_1', type: 'broken_heart', action: 'crack', sound: 'glass_break_soft' },
  { words: ['等', '原地', '站'], object: 'person_1', type: 'line_person', action: 'idle_waiting', sound: null },
  { words: ['走', '离开'], object: 'person_1', type: 'line_person', action: 'walk', sound: 'footstep_soft' },
  { words: ['奔跑', '跑', '冲'], object: 'person_1', type: 'line_person', action: 'run', sound: 'footstep_soft' },
  { words: ['拥抱'], object: 'person_2', type: 'two_people', action: 'hug', sound: 'heartbeat_soft' }
];

function includesAny(text, words) { return words.some((word) => text.includes(word)); }
function pickEmotion(text, tag) {
  if (tag) return tag;
  const found = EMOTION_RULES.find((rule) => includesAny(text, rule.words));
  return found ? found.key : '治愈';
}
function colorForEmotion(emotion) {
  const rule = EMOTION_RULES.find((item) => emotion.includes(item.key));
  return rule ? rule.color : ['#F6F3EE', '#DDE7F0'];
}
function sceneForText(text, theme) {
  if (theme) return theme;
  if (text.includes('雨')) return '雨后街边';
  if (text.includes('海')) return '海边';
  if (text.includes('夜') || text.includes('月')) return '夜晚城市';
  if (text.includes('校园')) return '校园';
  return '留白文案空间';
}
function buildElements(text) {
  const matched = OBJECT_RULES.filter((rule) => includesAny(text, rule.words));
  if (!matched.some((item) => item.type.includes('person'))) matched.push(OBJECT_RULES.find((item) => item.object === 'person_1'));
  return matched.map((rule, index) => ({
    id: rule.object,
    type: rule.type,
    position: { x: 80 + index * 70, y: rule.type === 'line_person' ? 330 : 190 + index * 22 },
    style: { strokeWidth: rule.type === 'line_person' ? 3 : 2, opacity: 0.82 }
  }));
}
function buildTimeline(text, elements) {
  const timeline = [
    { time: 0, target: 'text', action: 'glow', duration: 0.6, sound: 'soft_start' },
    { time: 0.55, target: 'text', action: 'text_to_line', duration: 0.8, sound: 'line_draw' }
  ];
  elements.forEach((element, index) => {
    const rule = OBJECT_RULES.find((item) => item.object === element.id) || {};
    timeline.push({ time: 1 + index * 0.45, target: element.id, action: rule.action || 'line_flow', duration: 3.5, sound: rule.sound });
  });
  if (!timeline.some((item) => item.sound === 'heartbeat_soft') && (text.includes('你') || text.includes('想'))) {
    timeline.push({ time: 4.2, target: 'heart_1', action: 'heartbeat_once', duration: 1, sound: 'heartbeat_soft' });
  }
  timeline.push({ time: 5.5, target: 'all', action: 'fade_out', duration: 0.5 });
  return timeline;
}
function parseCopy({ text, emotionTag = '', theme = '' }) {
  const cleanText = String(text || '').trim();
  const emotion = pickEmotion(cleanText, emotionTag);
  const scene = sceneForText(cleanText, theme);
  const colors = colorForEmotion(emotion);
  const elements = buildElements(cleanText);
  const timeline = buildTimeline(cleanText, elements);
  const sounds = [...new Set(timeline.map((item) => item.sound).filter(Boolean))];
  return {
    emotion,
    scene,
    keywords: cleanText.split(/[，。,.\s]/).filter(Boolean).slice(0, 8),
    objects: elements.map((item) => item.type),
    actions: timeline.filter((item) => item.target !== 'text' && item.target !== 'all').map((item) => ({ target: item.target, action: item.action })),
    sound: sounds,
    animation_style: '极简线条动画',
    duration: 6,
    preview_config: generatePreviewConfig(cleanText, emotion, scene, colors, elements),
    animation_manifest: generateManifest(`local_${Date.now()}`, cleanText, emotion, colors, elements, timeline)
  };
}
function generatePreviewConfig(text, emotion, scene, colors, elements) {
  const isLong = text.length > 28;
  return {
    layout: isLong ? 'poem_lines' : 'hero_sentence',
    fontSize: isLong ? 34 : 48,
    highlight: isLong ? text.split(/[。！？!?.]/)[0] : text,
    emotion,
    scene,
    background: { type: 'gradient', colors },
    accentColor: colors[1],
    elements: elements.slice(0, 4).map((item) => item.type),
    hint: '长按让文字活过来'
  };
}
function generateManifest(postId, text, theme, colors, elements, timeline) {
  return {
    post_id: postId,
    text,
    duration: 6,
    theme,
    background: { type: 'gradient', colors },
    elements,
    timeline
  };
}
module.exports = { parseCopy, generatePreviewConfig, generateManifest };
