#!/usr/bin/env python3
"""导出"急救信息卡"：把姓名、慢病、过敏、在吃的药、紧急联系人汇成一张卡，
打印出来给老人随身带——万一出事，旁人和医生一眼知道该怎么办、找谁。

用法：
  python scripts/emergency_card.py            # 打印纯文本卡（可贴冰箱）
  python scripts/emergency_card.py --html 急救卡.html   # 排成可打印网页

信息来自 config/health.yaml（慢病/过敏/血型）、config/medications.yaml、config/contacts.yaml。
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.emergency_card import build_card, card_data, card_text  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=None, help="排成可打印网页保存到此路径")
    args = ap.parse_args()

    agent = build_agent()
    data = card_data(agent)
    print("\n" + card_text(data) + "\n")
    if args.html:
        out = pathlib.Path(args.html)
        build_card(agent, out)
        print(f"🆘 已生成急救信息卡：{out}（浏览器打开可「打印」随身带）")


if __name__ == "__main__":
    main()
