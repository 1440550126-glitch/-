# LingMirror AI 视频 · 运行镜像（零依赖 Node 22：node:sqlite / 原生 fetch / http）
# 含 ffmpeg：AI 配音混音 / 烧录字幕 / 成片拼接导出 / 视频抽尾帧接龙
FROM node:22-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# 零依赖（无需 npm install）：直接拷贝灵境AI 子项目源码
COPY . /app/lingjing

ENV NODE_ENV=production \
    LINGJING_PORT=4399 \
    LINGJING_DB_PATH=/data/lingjing.sqlite \
    LINGJING_UPLOAD_DIR=/data/uploads \
    FFMPEG_PATH=ffmpeg
RUN mkdir -p /data /app/logs
EXPOSE 4399

# 健康检查：原生 fetch 打 /api/bootstrap（200 即 healthy）
HEALTHCHECK --interval=30s --timeout=8s --start-period=20s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:4399/api/bootstrap').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

# 日志同时落到挂载的 /app/logs（→ /opt/video/logs/video.log）
CMD ["sh","-c","node --disable-warning=ExperimentalWarning lingjing/server/index.js 2>&1 | tee -a /app/logs/video.log"]
