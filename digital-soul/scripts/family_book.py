#!/usr/bin/env python3
"""导出"家族册"：每位家人各一页（生平要点/性格/口头禅/TA 的记忆）+ 一段对谈，
编成一本自包含、可打印的 HTML，传家用。完全离线。

先在 config/family.yaml 登记家人（可给 memories）。用法：
  python scripts/family_book.py                 # 写到 data/family_book.html
  python scripts/family_book.py --topic 年夜饭   # 指定对谈话题
  python scripts/family_book.py --out 我们家.html
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.loader import build_agent  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="家常", help="对谈话题")
    ap.add_argument("--out", default=None, help="输出 HTML 路径（默认 data/family_book.html）")
    args = ap.parse_args()

    agent = build_agent()
    if not getattr(agent, "family", None) or not agent.family.get("members"):
        print("还没登记家人。先在 config/family.yaml 里加 members（可参考文件内示例）。")
        return
    html = agent.build_family_book(topic=args.topic)
    out = pathlib.Path(args.out) if args.out else (ROOT / "data" / "family_book.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"❦ 已生成家族册：{out}")
    print("   双击在浏览器打开；「打印 → 存为 PDF」即可传家。")


if __name__ == "__main__":
    main()
