# AI影视制作 Studio（网页版 MVP）

本仓库实现一个可本地运行的 AI 影视制作 Studio MVP。核心流程不是聊天页，而是完整的影片制作流水线：项目设置 → 大局观 → 剧本 → 选角 → 美术资产 → 分镜 → 结构化视频提示词 → Mock 视频生成 → FFmpeg 截帧 → 视觉监制 → 记忆挂点 → 连续性质检 → 自动修复重试 → MP4 导出。

## 技术栈

- 前端：Next.js、React、TypeScript、TailwindCSS、Zustand。
- 后端：FastAPI、Python、SQLAlchemy、Pydantic、Alembic。
- 数据库：PostgreSQL + pgvector（`memory_anchors.embedding_vector`）。
- 队列：Redis + Celery（MVP 预留 worker，核心 API 同步跑通完整闭环）。
- 视频处理：FFmpeg；OpenCV 依赖已预留。
- 存储：本地 `storage/`，后续可替换为 COS / S3 / MinIO。
- AI Provider：统一抽象接口，第一版使用 MockProvider。

## 目录结构

```text
ai-film-studio/
  frontend/                  # Next.js Web MVP
  backend/                   # FastAPI 服务
    app/agents/              # 导演、编剧、选角、美术、分镜、提示词、视频、截帧、视觉监制、记忆挂点、质检、修复 Agent
    app/providers/           # LLM/Image/Video/Vision/Embedding provider 抽象与 mock 实现
    app/services/            # 真实业务编排与状态流转
    alembic/                 # 数据库 migration
  storage/                   # 本地开发文件存储
  docker-compose.yml
  .env.example
  AGENTS.md
```

## 环境变量

复制示例文件：

```bash
cp .env.example .env
```

关键变量：

- `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_film_studio`
- `REDIS_URL=redis://localhost:6379/0`
- `STORAGE_ROOT=./storage`
- `DEFAULT_*_PROVIDER=mock`
- `MAX_SHOT_RETRY=3`
- `CONTINUITY_PASS_SCORE=85`

API Key 全部从 `.env` 读取，当前 Mock MVP 不需要真实 Key。

## Docker 启动

```bash
docker compose up --build
```

服务地址：

- 前端：http://localhost:3000
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 本地开发启动

### 1. 启动 PostgreSQL 与 Redis

```bash
docker compose up postgres redis
```

### 2. 后端安装与迁移

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

> `app.main` 也会在开发环境执行 `Base.metadata.create_all`，但正式开发请以 Alembic 为准。

### 3. 启动 Celery Worker

```bash
cd backend
source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info
```

### 4. 前端安装与启动

```bash
cd frontend
npm install
npm run dev
```

## MVP 验收流程

1. 打开 Dashboard，创建项目。
2. 进入 Story Bible 页面，点击“一键生成”。
3. 确认后生成 Script。
4. 进入 Casting，点击生成角色；页面有 60 秒倒计时，到时调用自动选择推荐分最高角色。
5. 进入 Assets，生成主场景、备用场景、道具、服装。
6. 进入 Shot List，生成 10 个 4-8 秒镜头。
7. 进入 Generation，可逐镜头执行：提示词 → Mock 视频 → 截帧 → 记忆挂点 → 质检；也可点击“一键生成完整短片流程”。
8. 进入 Memory Anchor 查看每个镜头识别的角色、动物、建筑、背景、道具、服装、天气、时间、色调、镜头方向与连续性说明。
9. 进入 Continuity Review 查看角色/背景/服装/道具/色彩/首尾帧衔接评分；低于 85 分可自动修复并重试，最多 3 次。
10. 进入 Export 导出拼接后的 MP4。

## 记忆挂点 / AI 视频监制数据流

每个镜头生成完成后，后端会执行：

1. 写入 `shots.video_path`。
2. `FrameExtractorAgent` 使用 FFmpeg 截取首帧、尾帧、关键帧。
3. `VisionSupervisorAgent` 调用 Vision Provider（MVP 为 mock）识别人物、动物、建筑、背景、道具、服装、天气、时间、色调、镜头方向和冲突。
4. `MemoryAnchorAgent` 写入 `memory_anchors`，包括 `entities_json`、`continuity_notes`、`style_lock`、帧路径与 1536 维 embedding。
5. 生成下一个镜头提示词前，自动读取上一个镜头 `last_frame_path` 作为当前 `first_frame_path`，并拼接最近记忆挂点为 `memory_context`。
6. `PromptDirectorAgent` 在结构化提示词中明确锁定角色脸型、发型、服装、建筑、背景、道具、动物、色调，并禁止换场景、换画风、新增无关人物。
7. `ContinuityAgent` 生成 `continuity_reports`。总分低于 `CONTINUITY_PASS_SCORE` 时进入 `RepairAgent`，自动重写提示词并重试。

## REST API

- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/generate-story-bible`
- `POST /api/projects/{project_id}/generate-script`
- `POST /api/projects/{project_id}/generate-characters`
- `POST /api/projects/{project_id}/select-character`
- `POST /api/projects/{project_id}/auto-select-characters`
- `POST /api/projects/{project_id}/generate-assets`
- `POST /api/projects/{project_id}/generate-shots`
- `POST /api/shots/{shot_id}/generate-prompt`
- `POST /api/shots/{shot_id}/generate-video`
- `POST /api/shots/{shot_id}/extract-frames`
- `POST /api/shots/{shot_id}/create-memory-anchor`
- `POST /api/shots/{shot_id}/review-continuity`
- `POST /api/shots/{shot_id}/repair-and-retry`
- `POST /api/projects/{project_id}/generate-all`
- `POST /api/projects/{project_id}/export`
- `GET /api/projects/{project_id}/memory-anchors`
- `GET /api/projects/{project_id}/continuity-reports`

## 测试与检查

```bash
cd backend && python -m compileall app
cd frontend && npm run build
```

如需完整视频闭环测试，请确保本机安装 FFmpeg，或使用 Docker 镜像运行后端。
