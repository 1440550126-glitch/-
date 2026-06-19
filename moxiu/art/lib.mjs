// 水墨美术渲染底座：把 SVG 字符串渲染成 PNG（加载书法字体 + 水墨滤镜）
import { Resvg } from '@resvg/resvg-js';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import fs from 'node:fs';

const HERE = dirname(fileURLToPath(import.meta.url));
export const FONTS = {
  brush:  'Ma Shan Zheng',   // 马善政毛笔楷书：清晰、用于标题与UI
  flow:   'Zhi Mang Xing',   // 之芒行书：飞动，用于主标题
  thin:   'Long Cang',       // 龙藏：清瘦手写，用于副标题
  hei:    'WenQuanYi Zen Hei' // 黑体保底
};
const FONT_FILES = [
  'MaShanZheng_400Regular.ttf',
  'ZhiMangXing_400Regular.ttf',
  'LongCang_400Regular.ttf',
  'wqy-zenhei.ttc',
].map(f => join(HERE, 'fonts', f));

// 渲染 SVG -> PNG 文件
export function render(svg, outPath, { width } = {}) {
  const resvg = new Resvg(svg, {
    fitTo: width ? { mode: 'width', value: width } : { mode: 'original' },
    font: { fontFiles: FONT_FILES, loadSystemFonts: false, defaultFontFamily: FONTS.brush },
    background: 'rgba(0,0,0,0)',
  });
  const png = resvg.render().asPng();
  fs.writeFileSync(outPath, png);
  return { bytes: png.length, w: resvg.render().width };
}
