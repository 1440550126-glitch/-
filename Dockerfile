# SoloCompany OS —— 零依赖 Node 22 服务端（多智能体 Agent 平台）
# 无第三方运行时依赖：不需要 npm install，构建快、镜像小。
FROM node:22-slim
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3003

# 拷贝运行所需代码（.dockerignore 已排除 .env / 数据库 / 日志 / 截图 / 向量化的开发件）
COPY . .

EXPOSE 3003

# 健康检查用 Node 内置 fetch，无需 curl/wget
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
  CMD ["node","-e","fetch('http://127.0.0.1:3003/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

CMD ["node","--disable-warning=ExperimentalWarning","server/index.js"]
