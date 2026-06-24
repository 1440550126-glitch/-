# 模型供应商与路由

多供应商并存，**按模型 ID 自动路由**（`providers.js` 的 `imageProviderOf` / `videoProviderOf`），各用各的 Key，未配 Key 安全回退本地占位。

## 视频（五家）
| 供应商 | 模型 ID 前缀/特征 | 鉴权 | 客户端 |
|---|---|---|---|
| 火山方舟 Seedance | `doubao-seedance-*` / 其余兜底 | Bearer（ARK_API_KEY） | `ark.js` arkVideoCreate/Get |
| Google Veo | `veo-*` | key（GOOGLE_API_KEY） | googleVeoCreate/Get |
| 阿里通义万相 | 含 `t2v`/`i2v` 或 `wan*video` | DashScope（DASHSCOPE_API_KEY） | dashscopeVideoCreate + dashscopeTaskGet |
| Vidu 全能参考 | `vidu*` | Token（VIDU_API_KEY） | viduReferenceVideoCreate/TaskGet |
| 可灵 Kling | `kling*` | **JWT(HS256)**（KLING_ACCESS_KEY+SECRET_KEY） | klingJWT + klingVideoCreate/TaskGet |

- 多主体参考（全能参考）只有 **Vidu / 可灵** 支持（`supportsMultiRef`）；其余只吃首帧。见 [consistency](consistency.md)。
- 时长按模型上限裁剪（`maxVideoDuration`）：见 [models](models.md)。

## 图像
| 供应商 | 模型 ID | 鉴权 |
|---|---|---|
| 火山 Seedream | `doubao-seedream-*` | ARK_API_KEY |
| OpenAI GPT Image | `gpt-image-1`/`dall*` | OPENAI_API_KEY（images/generations，有参考图走 images/edits 多图） |
| 阿里通义万相/Qwen-Image | `wanx*t2i` / `qwen-image` / `wan*` | DASHSCOPE_API_KEY |

- 顶配图像模型 `model_image_pro` 专给「角色身份板 / 全场景图 / 故事板图」用（`generateImage` 的 proKind）。

## 对话（LLM）
`arkChat` 按 `model_chat` 路由：`qwen*`/`qwq*`/`tongyi*` → DashScope OpenAI 兼容端点，否则火山方舟。`llmEnabled()` = 火山 Key 或 千问+DashScope。

## 加新供应商的套路
providerCfg 加 key/base → `*Enabled()` → `videoProviderOf`/`pickVideoProvider` 加分支 → create/get 客户端 → pipeline 的 createVideoTask/pollTask 加分支 → 设置页字段 + bootstrap providers 状态 + 模型清单 + .env + smoke。
