# AI影视制作 Studio 开发规范

- 本项目是 AI影视制作 Studio。
- 不允许做空壳页面；页面必须通过 `frontend/lib/api.ts` 调用后端接口并展示真实返回数据。
- 所有核心流程必须有真实数据流：Project → StoryBible → Script → Character → Asset → Shot → Prompt → Video → Frame → MemoryAnchor → ContinuityReport → Export。
- 所有 AI provider 必须可替换，统一继承 `backend/app/providers/base.py` 中的抽象接口。
- API Key 只能从 `.env` 读取，严禁写死在代码中。
- 视频生成第一版可以 mock，但接口必须真实，并且必须生成独立视频文件。
- 记忆挂点是核心功能，不能省略。
- 第二个镜头必须继承上一个镜头 `last_frame_path` 作为 `first_frame_path`。
- 所有状态必须写入数据库。
- 代码必须有类型标注。
- 后端接口必须有 Pydantic schema。
- 数据库模型必须有 Alembic migration。
- 前端页面必须能实际调用后端接口。
- README 必须写启动步骤。

## 项目结构

- `frontend/`: Next.js + React + TypeScript + TailwindCSS + Zustand。
- `backend/`: FastAPI + SQLAlchemy + Pydantic + Alembic。
- `storage/`: 本地视频、帧、角色图、资产图、导出文件。

## 常用命令

- 后端安装：`cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- 后端迁移：`cd backend && alembic upgrade head`
- 后端启动：`cd backend && uvicorn app.main:app --reload`
- Worker 启动：`cd backend && celery -A app.workers.celery_app worker --loglevel=info`
- 前端安装：`cd frontend && npm install`
- 前端启动：`cd frontend && npm run dev`
- 前端检查：`cd frontend && npm run lint`
- 后端检查：`cd backend && python -m compileall app`
