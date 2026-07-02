# 数字分身"大脑"容器。
# 注意：摄像头 / 麦克风 / 桌面 GUI 依赖宿主设备，容器内默认不可用；
# 本镜像主要用于跑常驻"大脑"（记忆 + 授权 + 巩固），大模型建议用局域网 Ollama。
FROM python:3.11-slim

WORKDIR /app

# 只装核心依赖；语音/视觉等可选能力按需在镜像里再加
RUN pip install --no-cache-dir pyyaml

COPY . .

# 大模型地址：指向宿主或局域网的 Ollama
ENV DSOUL_LLM_HOST=http://host.docker.internal:11434 \
    DSOUL_LLM_MODEL=qwen2.5:7b-instruct \
    PYTHONUNBUFFERED=1

# 默认跑常驻服务（无摄像头）。也可：docker run --rm -it digital-soul python scripts/chat.py
CMD ["python", "scripts/daemon.py", "--no-vision"]
