"""统一命令行入口：`digital-soul <命令> [参数]`。

安装后（`pip install -e .`）即可用，例如：
    digital-soul demo
    digital-soul chat
    digital-soul daemon --voice --web

实现上把子命令转发到 scripts/ 下对应脚本（保持单一实现，避免重复逻辑）。
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

_CMDS = {
    "demo": "demo.py",
    "chat": "chat.py",
    "desktop": "desktop.py",
    "doctor": "doctor.py",
    "daemon": "daemon.py",
    "timeline": "timeline.py",
    "sleep": "sleep.py",
    "watch": "watch.py",
    "ingest": "ingest.py",
    "voice": "voice_chat.py",
    "persona": "persona.py",
}


def _usage() -> str:
    return (
        "用法: digital-soul <命令> [参数]\n"
        "命令:\n"
        "  demo        端到端演示（看一遍'一天'）\n"
        "  chat        命令行对话\n"
        "  desktop     桌面图形界面\n"
        "  voice       语音对话\n"
        "  daemon      常驻服务（感知/语音/网页/巩固）\n"
        "  watch       摄像头认人 + 主动打招呼\n"
        "  timeline    情感时间线\n"
        "  sleep       睡眠巩固\n"
        "  ingest      导入记忆/文档/人脸\n"
        "  persona     切换人格（套用 examples 模板）\n"
        "  doctor      环境自检\n"
    )


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(_usage())
        return
    cmd = sys.argv[1]
    if cmd not in _CMDS:
        print(f"未知命令: {cmd}\n\n{_usage()}")
        sys.exit(2)
    script = _SCRIPTS / _CMDS[cmd]
    if not script.exists():
        sys.exit(f"找不到 {script}\n（请用 `pip install -e .` 可编辑安装，或直接在源码目录运行 scripts/）")
    sys.argv = [str(script)] + sys.argv[2:]  # 透传剩余参数给脚本
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
