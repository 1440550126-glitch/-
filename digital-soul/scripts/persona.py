#!/usr/bin/env python3
"""一键切换人格：套用 config/examples 里的模板。

  digital-soul persona                       # 列出所有人格 + 当前身份
  digital-soul persona flirty-girlfriend     # 切到"色色女友"（恋人类自动套用配套关系）
  digital-soul persona gentle-mom --keep-relationships
  digital-soul persona flirty-girlfriend --seed-memory   # 同时换上"我们的故事"(会先备份旧记忆)
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.personas import COMPANION, apply_persona, current_name, list_personas  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", help="人格名（不填则列出全部）")
    ap.add_argument("--keep-relationships", action="store_true", help="不替换关系配置")
    ap.add_argument("--seed-memory", action="store_true", help="同时换上该人设的示例记忆（会先备份旧记忆）")
    args = ap.parse_args()

    av = list_personas()
    if not args.name:
        print(f"当前身份：{current_name()}\n")
        print("可用人格（digital-soul persona <名字>）：")
        for n, s in av.items():
            tag = "💕" if n in COMPANION else "👪"
            print(f"  {tag} {n.ljust(18)} {s[:34]}")
        return

    if args.name not in av:
        print(f"没有这个人格：{args.name}\n可用：{', '.join(av)}")
        sys.exit(2)

    info = apply_persona(args.name, keep_relationships=args.keep_relationships, seed_memory=args.seed_memory)
    print("✅ 已切换：")
    for c in info["changed"]:
        print("   -", c)
    print(f"\n当前身份：{current_name()}   试试：digital-soul chat")


if __name__ == "__main__":
    main()
