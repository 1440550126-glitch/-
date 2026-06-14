#!/usr/bin/env bash
# 一键安装（Debian / Raspberry Pi OS / Ubuntu）。
#   ./scripts/install.sh          # 核心（够用）
#   ./scripts/install.sh --full   # 额外装语音 + 视觉依赖
set -e

FULL=0
[ "${1:-}" = "--full" ] && FULL=1
cd "$(dirname "$0")/.."

echo "==> 安装系统依赖"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3-venv python3-pip python3-tk git
  if [ "$FULL" -eq 1 ]; then
    sudo apt-get install -y python3-opencv espeak-ng portaudio19-dev
  fi
else
  echo "（非 apt 系统：请手动安装 python3-venv / python3-tk / git）"
fi

echo "==> 创建虚拟环境并安装 Python 依赖"
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install --upgrade pip
pip install pyyaml
if [ "$FULL" -eq 1 ]; then
  pip install faster-whisper pyttsx3 sounddevice numpy face_recognition
fi

echo "==> 冒烟测试"
python tests/test_authority.py >/dev/null && echo "   authority ✓"
python tests/test_memory.py    >/dev/null && echo "   memory ✓"

echo "==> 自检"
python scripts/doctor.py || true

cat <<'TIP'

✅ 安装完成。下次使用前先激活环境：
   source .venv/bin/activate

常用命令：
   python scripts/chat.py        # 命令行对话
   python scripts/desktop.py     # 桌面界面
   python scripts/daemon.py      # 常驻服务（感知 + 巩固）
   python scripts/doctor.py      # 随时自检

接本地大模型（可选）：装 Ollama 后 `ollama pull qwen2.5:7b-instruct`，
或设 DSOUL_LLM_HOST 指向局域网的 Ollama。
TIP
