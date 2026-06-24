# 最新模型与时长

模型 ID 以各家控制台为准；清单里带「核对ID」的需到控制台复制准确 ID/接入点替换。默认仍用确认可用的稳定 ID（开箱不破）。

## 时长上限（`maxVideoDuration`）
| 模型 | 最长 |
|---|---|
| Seedance 2.5 | 30s |
| Seedance 2.0 | 15s |
| 可灵 Kling | 10s（5/10） |
| 通义万相 | 10s |
| Veo / Vidu | 8s |
| 默认（Seedance 1.0） | 12s |
- 分镜解析期存「意图时长」上限 30；出片时按所选模型上限裁剪。四个出片入口（单片/单镜/批量/全流程/全能参考）共用项目级「视频模型」选择器。

## 默认（DEFAULTS / 设置可改）
- 对话 `doubao-seed-1-6-250615`；图 `doubao-seedream-4-0-250828`；视频 `doubao-seedance-1-0-pro-250528`。
- 顶配图 `model_image_pro`（身份板/全场景/故事板用）。

## 可选清单（创作框下拉，2026 刷新）
- 视频：Seedance 2.5/2.0、Veo 3.1/3、通义万相 2.5/2.2/2.1、Vidu Q2/Q1、可灵 2.5/2.1/1.6。
- 图像：Seedream 5.0/4.0、GPT Image、通义万相 2.5/2.1 文生图、Qwen-Image。
- Sora 2 已被 OpenAI 弃用（2026-04），未纳入。

## 改默认 / 加模型
设置页改 `model_*`，或在 `ark.js DEFAULTS.model_video_options` / `providers.js model_image_options` 加行。路由靠模型 ID 前缀（见 [providers](providers.md)）。
