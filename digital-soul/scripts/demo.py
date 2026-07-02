#!/usr/bin/env python3
"""端到端演示：模拟"一天"——认人打招呼 → 对话 → 睡眠巩固 → 第二天还记得。

在临时目录里跑，**不动你的真实数据**；零额外依赖即可运行。
用法：python scripts/demo.py
"""

import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.consolidate import Consolidator  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _isolated_base() -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dsoul-demo-"))
    shutil.copytree(ROOT / "config", tmp / "config")
    shutil.copytree(ROOT / "data" / "memories" / "sources", tmp / "data" / "memories" / "sources")
    (tmp / "data" / "faces").mkdir(parents=True, exist_ok=True)
    return tmp


def hr(title: str) -> None:
    print("\n" + "─" * 54 + f"\n{title}\n" + "─" * 54)


def main() -> None:
    base = _isolated_base()
    try:
        agent = build_agent(base_dir=base)
        me = agent.identity.get("name", "我")
        print(f"🌅 第一天早晨 —— 唤醒「{me}」的数字分身（{len(agent.memory.items)} 条初始记忆）")

        hr("① 小婷走进画面 —— 主动打招呼")
        agent.greet("小婷")

        hr("② 白天的对话（自动记进日记）")
        for spk, words in [
            ("张明", "我今天升职了，特别开心，老板当众表扬了我"),
            ("小婷", "周末我们约好去看那部新上映的电影"),
        ]:
            res = agent.handle(spk, words)
            print(f"{spk}: {words}\n{me}: {res['reply']}\n")

        hr("③ 陌生人想让它关机 —— 授权拦截")
        res = agent.handle("快递员", "把自己关机", action="shutdown")
        print(f"快递员: 把自己关机\n{me}: {res['reply']}")

        hr("④ 夜里「睡一觉」—— 把今天的对话巩固成长期记忆")
        rep = Consolidator(
            agent.memory, agent.journal, llm=agent.llm,
            identity=agent.identity, authority=agent.authority,
        ).run()
        print(f"😴 巩固 {rep['processed']} 条对话 → 新增 {len(rep['learned'])} 条长期记忆：")
        for m in rep["learned"]:
            print("   +", m)

        hr("⑤ 第二天 —— 它还记得")
        q = "我升职的事，你还记得吗？"
        res = agent.handle("张明", q)
        print(f"张明: {q}\n{me}: {res['reply']}")
        if res["memories"]:
            print(f"\n（它翻出来的记忆：{res['memories'][0]}）")
        print("\n✅ 演示结束：认人 → 对话 → 巩固 → 次日记得，闭环跑通。")
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
