#!/usr/bin/env python3
"""贾维斯语音闭环演示：模拟 `--voice --wake 贾维斯` 的一段对话。

不需要麦克风、不动真实数据（临时目录里跑）。串起：
唤醒待命 → 态势简报 → 控设备 → 多步编排 → 场景 → 设定自动化 →
定时/进门自动触发 → 晨间主动简报。
用法：python scripts/jarvis_demo.py
"""

import pathlib
import shutil
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.butler import daily_brief  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
WAKE = "贾维斯"
OWNER = "张明"


def _isolated_base() -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dsoul-jarvis-"))
    shutil.copytree(ROOT / "config", tmp / "config")
    shutil.copytree(ROOT / "data" / "memories" / "sources", tmp / "data" / "memories" / "sources")
    (tmp / "data" / "faces").mkdir(parents=True, exist_ok=True)
    return tmp


def heard(agent, raw: str) -> None:
    """模拟语音回合：先过唤醒词，再交给分身，最后"播报"。"""
    print(f"🎙️  {raw}")
    if WAKE not in raw:
        print("    …（没有唤醒词，贾维斯保持安静）\n")
        return
    text = raw.split(WAKE, 1)[1].strip("，,。.!！?？、 ")
    if not text:
        print("🔊 贾维斯：在的，有什么吩咐？\n")
        return
    reply = agent.handle(OWNER, text)["reply"]
    print(f"🔊 贾维斯：{reply}\n")


def auto(tag: str, notices) -> None:
    for n in notices:
        print(f"🔊 [{tag}] 贾维斯：{n}")
    if notices:
        print()


def main() -> None:
    base = _isolated_base()
    try:
        agent = build_agent(base_dir=base)
        print("🤖 贾维斯语音助手演示（模拟 --voice --wake 贾维斯，不动真实数据）\n")

        heard(agent, "老婆：晚饭想吃什么呀")          # 背景闲聊，无唤醒 → 安静
        heard(agent, "贾维斯")                         # 点名 → 待命
        heard(agent, "贾维斯，简报")                   # 态势简报
        heard(agent, "贾维斯，把灯打开、空调调到24度，再放点音乐")  # 多步编排
        heard(agent, "贾维斯，我回来了")               # 场景：回家模式
        heard(agent, "贾维斯，每天22点提醒锁门")        # 定时自动化
        heard(agent, "贾维斯，我一进门就开灯")          # 进门自动化
        heard(agent, "贾维斯，温度低于18就开空调")      # 条件自动化

        print("—— 接下来是它「自己动」的部分 ——\n")
        auto("定时", agent.check_time_triggers(datetime.now().replace(hour=22, minute=0)))
        agent.sensors["temperature"] = 15
        auto("条件", agent.check_conditions())
        auto("进门", agent.fire_event("enter", OWNER))

        who = agent.authority.resolve(OWNER)
        morning = datetime.now().replace(hour=8, minute=0)
        print("🌅 （清晨 8 点，摄像头第一次认出你 —— 不用开口，它主动汇报）")
        print(f"🔊 贾维斯：{daily_brief(agent, present=[OWNER], addr=agent._addr(who), now=morning)}\n")

        print("✅ 演示结束：唤醒 → 简报 → 控设备 → 编排 → 场景 → 自动化 → 主动简报，全程走授权。")
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
