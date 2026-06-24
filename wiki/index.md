# 项目 Wiki · 总索引

本仓库的自维护知识库（LLM Wiki 范式）。维护规则见 `.claude/skills/project-wiki/SKILL.md`。
开工先查相关页，收尾把新知识沉淀回来。

## 仓库里有什么
两套独立 App + 一个部署包：
- **灵境AI（`lingjing/`）** — AI 短剧/短片创作工坊（本知识库主要对象）。
- **AI句灵（仓库根 `server/` `web/` `admin/` `miniprogram/`）** — 文案社交圈 App。
- 音乐站（music.lingmirror.com.cn）= **独立仓库**，不在此 repo；经 MCP 与灵境AI 共享知识库。

## 页目录
| 页 | 内容 |
|---|---|
| [architecture](architecture.md) | 灵境AI 架构：零依赖 Node、目录、数据流、Agent/MCP |
| [providers](providers.md) | 五家视频 + 多家图像供应商、鉴权、按模型 ID 路由 |
| [models](models.md) | 最新模型 ID、时长上限、默认/可选清单 |
| [consistency](consistency.md) | 一致性手法：身份板/视觉签名/锁脸不锁衣/微表情/光影/全能参考/故事板 |
| [deploy](deploy.md) | 部署包（Docker+Caddy）、CI/CD、video.lingmirror.com.cn |
| [llm-wiki](llm-wiki.md) | 运行时知识库（wiki_pages + MCP 共享给音乐站/Agent） |

## 速记
- 测试：`node lingjing/scripts/smoke.mjs`（当前 218/218）。零依赖，Node ≥22.5。
- 分支：开发在 `claude/wizardly-fermi-y32aue`，合并到 `main`。
- 安全：API Key/密钥只走环境变量/服务器文件，永不入库/对话。
