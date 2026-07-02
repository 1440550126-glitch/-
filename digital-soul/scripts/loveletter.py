#!/usr/bin/env python3
"""写一封情书：以 TA 本人的口吻，给老伴写一封走心的信，可打印珍藏。

用法：
  python scripts/loveletter.py                    # 打印到屏幕
  python scripts/loveletter.py --occasion 纪念日   # 指定由头（纪念日/生日/思念）
  python scripts/loveletter.py --html 情书.html    # 排成信纸网页保存

有本地大模型（Ollama 等）会自动润色；没有也能用模板写一封。
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.loader import build_agent  # noqa: E402
from dsoul.loveletter import letter_html  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--occasion", default="", help="由头：纪念日 / 生日 / 思念")
    ap.add_argument("--html", default=None, help="排成信纸网页保存到此路径")
    args = ap.parse_args()

    agent = build_agent()
    if not getattr(agent, "spouse", None):
        print("（还没认出老伴：在 config/spouse.yaml 里填一下，或在 family.yaml 里"
              "标明谁是老伴/老婆/老公。）")
        return
    letter = agent.write_love_letter(args.occasion)
    if not letter:
        print("（写不出来——先在 config/spouse.yaml 里补点我们的故事吧。）")
        return
    print("\n" + letter + "\n")
    if args.html:
        out = pathlib.Path(args.html)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(letter_html(letter, agent.spouse), encoding="utf-8")
        print(f"💌 已排成信纸：{out}（浏览器打开可「打印 → 存为 PDF」珍藏）")


if __name__ == "__main__":
    main()
