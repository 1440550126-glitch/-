# 墨修 · 美术资产（水墨风）

纯手绘 **SVG**（矢量笔触 + 水墨晕染滤镜 + 宣纸纹理）→ 渲染成 PNG。
不依赖外部图库，改一行代码就能重出图，之后可直接喂给游戏端（Canvas / 小游戏）。

## 重新出图

```bash
cd moxiu/art
npm i                 # 装 @resvg/resvg-js
bash fetch-fonts.sh   # 取回书法字体（马善政楷书 / 之芒行书 / 龙藏 + 黑体保底）
node gen.mjs all      # 输出 character.png / scene.png / start-screen.png
node gen.mjs char     # 也可单出某一张：char | scene | start | solo
```

## 文件

| 文件 | 说明 |
|------|------|
| `lib.mjs` | 渲染底座：加载字体、SVG→PNG |
| `gen.mjs` | 美术生成器：调色盘、滤镜、山脊/云雾/松/印章/角色等元件 + 三张合成场景 |
| `character.png` | 角色设定：男女修士（坤·法修 / 乾·剑修） |
| `scene.png` | 水墨山水：游戏世界背景 |
| `start-screen.png` | 开始/创角界面（六道选择 + 乾坤） |

## 美术约定

- 调色：宣纸米色 + 浓/中/淡三级墨 + 朱砂（印/穗）+ 石青（绦）。克制用色，留白为主。
- 滤镜：`paper` 宣纸纹理、`wet/wetSoft` 湿笔晕染（仅用于小元件，大色块用 `mtnEdge` 高斯柔边以规避 resvg 位移崩溃）。
- 角色：Q版约 2.5 头身，清线 + 浅墨染；男女以发型 / 绦色 / 额钿区分。
