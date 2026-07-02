#!/usr/bin/env python3
"""导出"数字纪念册"：把 TA 的一生编成一页自包含 HTML，可保存 / 双击打开 / 打印成 PDF。

完全离线，无网络、无外链（照片也以 base64 自包含进 HTML）。用法：
  python scripts/keepsake.py                 # 写到 data/keepsake.html
  python scripts/keepsake.py --out 外公.html  # 指定文件名
  python scripts/keepsake.py --photos 相册/   # 指定照片文件夹（默认 data/photos/）

把照片放进 data/photos/（文件名会成为图注，如 "1990 出生.jpg"），就会嵌进"影像"。
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.keepsake import build_keepsake  # noqa: E402
from dsoul.loader import build_agent  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="输出 HTML 路径（默认 data/keepsake.html）")
    ap.add_argument("--photos", default=None, help="照片文件夹（默认 data/photos/）")
    args = ap.parse_args()

    agent = build_agent()
    photos_dir = pathlib.Path(args.photos) if args.photos else (ROOT / "data" / "photos")
    html = build_keepsake(agent, photos_dir=photos_dir)
    out = pathlib.Path(args.out) if args.out else (ROOT / "data" / "keepsake.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    name = agent.identity.get("name", "TA")
    print(f"🕯️ 已为「{name}」生成数字纪念册：{out}")
    print("   双击即可在浏览器打开；想留 PDF 就在浏览器里「打印 → 存为 PDF」。")


if __name__ == "__main__":
    main()
