#!/usr/bin/env python3
"""导出"家珍册"：把分身替这个家守着的念想汇成一页本地 HTML——
家谱、遗物、家史故事、做人道理与手艺、口头语录、家传菜、家族病史、人情往来、遗言家训。

完全离线、无网络、无外链。用法：
  python scripts/heritage.py                  # 写到 data/heritage.html
  python scripts/heritage.py --out 家珍.html   # 指定文件名

内容来自 config/ 下各项配置（family / heirlooms / health / stories / teachings /
sayings / recipes / favors / legacy / mannerisms）。补得越全，这页越厚重。
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.heritage import build_heritage  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="输出 HTML 路径（默认 data/heritage.html）")
    args = ap.parse_args()

    agent = build_agent()
    out = pathlib.Path(args.out) if args.out else (ROOT / "data" / "heritage.html")
    build_heritage(agent, out)
    name = agent.identity.get("name", "TA")
    print(f"📒 已为「{name}」生成家珍册：{out}")
    print("   双击即可在浏览器打开；想留 PDF 就在浏览器里「打印 → 存为 PDF」。")


if __name__ == "__main__":
    main()
