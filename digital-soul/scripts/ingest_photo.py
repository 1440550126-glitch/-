#!/usr/bin/env python3
"""把一张照片变成「带日期的记忆」，让"那张全家福"也能被想起。

人物可手动指定，或（装了视觉后端时）让人脸识别自动认出。
用法：
  python scripts/ingest_photo.py 全家福.jpg --people 小婷,张爸 --when 2021 --place 老家院子 --caption "一起包饺子" --write
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.loader import _load_yaml  # noqa: E402
from dsoul.memory import Memory  # noqa: E402
from dsoul.perception import build_perception  # noqa: E402
from dsoul.photo import identify_faces, member_tags, photo_memory  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="照片路径")
    ap.add_argument("--people", default="", help="照片里的人，逗号分隔")
    ap.add_argument("--when", default=None, help="年份，如 2021")
    ap.add_argument("--place", default=None, help="地点")
    ap.add_argument("--caption", default=None, help="一句描述")
    ap.add_argument("--write", action="store_true", help="写入长期记忆（默认仅预览）")
    args = ap.parse_args()

    people = [p.strip() for p in args.people.split(",") if p.strip()]
    # 没手动给人，就试试人脸识别
    if not people:
        from dsoul.authority import Authority
        auth = Authority(_load_yaml(ROOT / "config" / "relationships.yaml"))
        perc = build_perception(ROOT / "data" / "faces", auth)
        people = identify_faces(perc, args.image)
        if people:
            print(f"👁️ 人脸识别认出：{ '、'.join(people) }")

    mem_text = photo_memory(people, when=args.when, caption=args.caption, place=args.place)
    print("📷 这张照片将成为记忆：")
    print("   " + mem_text)

    # 照片里若有登记在册的家人，这条记忆也归到 TA 名下（多人合一·专属记忆）
    mtags = member_tags(people, _load_yaml(ROOT / "config" / "family.yaml"))
    if mtags:
        print(f"👪 归属到家人：{ '、'.join(t.split(':', 1)[1] for t in mtags) }")

    if args.write:
        mem = Memory(ROOT / "data" / "memories" / "index.json")
        before = len(mem.items)
        mem.add(mem_text, source=f"photo:{pathlib.Path(args.image).name}",
                tags=["photo"] + people + mtags, when=args.when)
        print(f"✅ 已写入长期记忆（+{len(mem.items) - before}）。它会出现在时间线与关系图谱里。")
    else:
        print("（预览模式。加 --write 才会真正写入。）")


if __name__ == "__main__":
    main()
