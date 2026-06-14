#!/usr/bin/env python3
"""和你的数字分身对话（命令行）。

用法：
    python scripts/chat.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.annotate import EMOJI  # noqa: E402
from dsoul.consolidate import Consolidator  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402

HELP = """\
可用命令：
  /as <名字>    切换"现在是谁在跟我说话"（试不同人的权限和感情）
  /do <动作>    让我执行动作：/do move  /do protect  /do shutdown
  /who          列出我认识的人和信任等级
  /mem <文字>   临时给我加一条记忆
  /timeline     按时间线 + 情感回顾我的记忆
  /sleep        睡一觉：把刚才的对话巩固成长期记忆
  /help         显示帮助
  /quit         退出
直接打字 = 跟我聊天。
"""


def _default_owner(agent) -> str:
    for p in agent.authority.people.values():
        if p.get("trust") == "owner":
            return p["name"]
    return "我"


def main() -> None:
    agent = build_agent()
    name = agent.identity.get("name", "我")
    llm_state = "已接入 ✅" if agent.llm.available else "未接入（降级模式）⚠️  装 Ollama 后自动启用"
    print(f"🧠 已唤醒「{name}」的数字分身")
    print(f"   本地大模型：{llm_state}")
    print(f"   记忆检索：{agent.memory.embedder.mode}（{len(agent.memory.items)} 条记忆）")
    print(f"   人脸识别：{'可用 ✅' if agent.perception.available else '未启用'}")
    print(HELP)

    speaker = _default_owner(agent)
    print(f"（当前说话人：{speaker}）")

    while True:
        try:
            line = input(f"\n{speaker} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("/quit", "/exit"):
            break
        if line == "/help":
            print(HELP)
            continue
        if line == "/timeline":
            cur = None
            for it in agent.memory.timeline():
                when = it.get("when") or "时间未知"
                if when != cur:
                    print(f"【{when}】")
                    cur = when
                emo = it.get("emotion", "平静")
                print(f"  {EMOJI.get(emo, '·')} {emo}  {it['text']}")
            continue
        if line == "/sleep":
            report = Consolidator(
                agent.memory, agent.journal, llm=agent.llm,
                identity=agent.identity, authority=agent.authority,
            ).run()
            print(f"😴 巩固了 {report['processed']} 条对话，新增 {len(report['learned'])} 条长期记忆：")
            for m in report["learned"]:
                print(f"  + {m}")
            continue
        if line == "/who":
            for p in agent.authority.people.values():
                who = agent.authority.resolve(p["name"])
                flag = "🛡️守护" if who["guard"] else ("🚫不服从" if not who["obey"] else "")
                print(f"  - {who['name']}（{who['relation']}）信任={who['trust']} {flag}")
            continue
        if line.startswith("/as "):
            speaker = line[4:].strip()
            print(f"（现在说话人切换为：{speaker}）")
            continue
        if line.startswith("/mem "):
            agent.memory.add(line[5:].strip(), source="chat")
            print("（记住了）")
            continue
        if line.startswith("/do "):
            action = line[4:].strip()
            res = agent.handle(speaker, f"（请求执行：{action}）", action=action)
            if res.get("action_allowed"):
                print(f"  ✅ 已执行：{action}")
            else:
                print(f"  ⛔ {res['reply']}")
            continue

        res = agent.handle(speaker, line)
        print(f"{name}: {res['reply']}")


if __name__ == "__main__":
    main()
