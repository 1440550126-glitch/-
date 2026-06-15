// 离线逻辑自测（不依赖网络与 wx-server-sdk）：node dewatermark/scripts/test.js
const assert = require('assert');
const path = require('path');

const R = (p) => require(path.join(__dirname, '..', p));

let n = 0;
const ok = (name) => {
  n += 1;
  console.log('  ✓', name);
};

// 1) 链接提取与平台识别
(() => {
  const { detect, extractUrl } = R('miniprogram/utils/link');
  const dy = detect('7.88 复制打开抖音，看看【作品】https://v.douyin.com/abc123/ 很棒');
  assert.strictEqual(dy.platform, 'douyin');
  assert.strictEqual(dy.url, 'https://v.douyin.com/abc123/');
  assert.ok(dy.supported);

  assert.strictEqual(detect('https://www.kuaishou.com/f/xYz').platform, 'kuaishou');
  assert.strictEqual(detect('看笔记 http://xhslink.com/aB12cd').platform, 'xiaohongshu');
  assert.strictEqual(detect('随便一句话没有链接').url, '');
  assert.strictEqual(detect('https://example.com/x').supported, false);
  assert.strictEqual(extractUrl('xx https://v.douyin.com/q/）'), 'https://v.douyin.com/q/');
  ok('link.detect / extractUrl');
})();

// 2) 平台调度
(() => {
  const parsers = R('cloudfunctions/parse/parsers/index');
  assert.strictEqual(parsers.detectPlatform('https://v.douyin.com/x'), 'douyin');
  assert.strictEqual(parsers.detectPlatform('https://kuaishou.com/x'), 'kuaishou');
  assert.strictEqual(parsers.detectPlatform('https://xiaohongshu.com/x'), 'xiaohongshu');
  assert.strictEqual(parsers.detectPlatform('https://youtube.com/x'), 'unknown');
  ok('parsers.detectPlatform');
})();

// 3) 抖音内部解析逻辑（合成 _ROUTER_DATA 固件）
(() => {
  const { _t } = R('cloudfunctions/parse/parsers/douyin');

  // 去水印 URL 改写
  assert.strictEqual(
    _t.noWatermark('https://aweme.snssdk.com/aweme/v1/playwm/?video_id=1&watermark=1'),
    'https://aweme.snssdk.com/aweme/v1/play/?video_id=1&watermark=0'
  );

  // 字符串感知的 JSON 截取：desc 里含有花括号也不会截断
  const html =
    'prefix window._ROUTER_DATA = ' +
    JSON.stringify({
      loaderData: {
        'video_(id)/page': {
          videoInfoRes: {
            item_list: [
              {
                desc: '标题里有 {花括号} 也不怕',
                author: { nickname: '小明' },
                video: {
                  play_addr: { url_list: ['http://x/playwm/a', 'https://aweme.snssdk.com/playwm/a'] },
                  cover: { url_list: ['https://c/cover.jpg'] },
                },
              },
            ],
          },
        },
      },
    }) +
    ';</script> suffix {unbalanced';

  const data = _t.extractRouterData(html);
  assert.ok(data && data.loaderData, 'router data parsed');
  const detail = _t.pickDetail(data);
  assert.ok(detail && detail.desc.includes('花括号'));

  const r = _t.normalize(detail, '123');
  assert.strictEqual(r.type, 'video');
  assert.strictEqual(r.platform, 'douyin');
  assert.strictEqual(r.title, '标题里有 {花括号} 也不怕');
  assert.strictEqual(r.author, '小明');
  // 应优先 https 且去掉 playwm
  assert.strictEqual(r.url, 'https://aweme.snssdk.com/play/a');
  assert.strictEqual(r.cover, 'https://c/cover.jpg');
  ok('douyin: extract / pickDetail / normalize (video)');

  // 图集
  const imgDetail = {
    desc: '九宫格',
    images: [
      { url_list: ['https://i/1.jpg'] },
      { url_list: ['https://i/2.jpg'] },
    ],
  };
  const ir = _t.normalize(imgDetail, '');
  assert.strictEqual(ir.type, 'image');
  assert.deepStrictEqual(ir.images, ['https://i/1.jpg', 'https://i/2.jpg']);
  assert.strictEqual(ir.cover, 'https://i/1.jpg');
  ok('douyin: normalize (image set)');
})();

// 4) meta 标签提取
(() => {
  const { meta, metaAll } = R('cloudfunctions/parse/parsers/meta');
  const html =
    '<meta property="og:title" content="标题A">' +
    '<meta name="og:video" content="https://v/x.mp4">' +
    '<meta property="og:image" content="https://i/1.jpg">' +
    '<meta property="og:image" content="https://i/2.jpg">';
  assert.strictEqual(meta(html, 'og:title'), '标题A');
  assert.strictEqual(meta(html, 'og:video'), 'https://v/x.mp4');
  assert.strictEqual(meta(html, 'og:image'), 'https://i/1.jpg'); // 取首个
  assert.deepStrictEqual(metaAll(html, 'og:image'), ['https://i/1.jpg', 'https://i/2.jpg']);
  // 反序写法（content 在 property 之前）也能兜底取到
  assert.strictEqual(
    meta('<meta content="https://i/9.jpg" property="og:image">', 'og:image'),
    'https://i/9.jpg'
  );
  ok('meta / metaAll');
})();

// 5) 第三方结果映射
(() => {
  const { mapResult } = R('cloudfunctions/parse/lib/thirdparty');
  const v = mapResult({ data: { video_url: 'https://v/x.mp4', title: 'T', platform: 'douyin' } });
  assert.strictEqual(v.type, 'video');
  assert.strictEqual(v.url, 'https://v/x.mp4');
  const im = mapResult({ result: { images: ['https://i/1.jpg'], title: 'P' } });
  assert.strictEqual(im.type, 'image');
  assert.strictEqual(mapResult({}), null);
  ok('thirdparty.mapResult');
})();

// 6) 结果结构规范化
(() => {
  const { videoResult, imageResult } = R('cloudfunctions/parse/lib/result');
  const v = videoResult({ platform: 'douyin', title: '  x  ', url: 'u' });
  assert.strictEqual(v.title, 'x');
  assert.strictEqual(v.type, 'video');
  const im = imageResult({ images: ['a', '', null, 'b'] });
  assert.deepStrictEqual(im.images, ['a', 'b']);
  assert.strictEqual(im.cover, 'a');
  ok('result shapes');
})();

console.log(`\n全部通过：${n} 组用例 ✅`);
