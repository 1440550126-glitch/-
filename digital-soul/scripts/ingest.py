#!/usr/bin/env python3
"""把记忆 / 文档 / 人脸喂给数字分身。

用法：
    python scripts/ingest.py text "我今天答应了小婷周末去看电影"
    python scripts/ingest.py doc  我的日记.md
    python scripts/ingest.py face xiaoting /路径/小婷的照片.jpg
"""

import argparse
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.loader import build_agent, split_paragraphs  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent


def read_document(path: pathlib.Path) -> str:
    suf = path.suffix.lower()
    if suf in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    if suf == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception:
            raise SystemExit("读取 PDF 需要 pypdf：pip install pypdf")
        reader = PdfReader(str(path))
        return "\n\n".join((pg.extract_text() or "") for pg in reader.pages)
    raise SystemExit(f"暂不支持的文档类型：{suf}（支持 .txt/.md/.pdf）")


def main() -> None:
    ap = argparse.ArgumentParser(description="给数字分身导入记忆/文档/人脸")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_text = sub.add_parser("text", help="添加一条文字记忆")
    p_text.add_argument("content")

    p_doc = sub.add_parser("doc", help="摄取一个文档(.txt/.md/.pdf)")
    p_doc.add_argument("path")

    p_face = sub.add_parser("face", help="登记一张人脸：face <face_id> <图片>")
    p_face.add_argument("face_id")
    p_face.add_argument("image")

    args = ap.parse_args()
    agent = build_agent()

    if args.cmd == "text":
        agent.memory.add(args.content, source="cli")
        print("✅ 已记住。")

    elif args.cmd == "doc":
        path = pathlib.Path(args.path)
        if not path.exists():
            raise SystemExit(f"找不到文件：{path}")
        n = 0
        for para in split_paragraphs(read_document(path)):
            agent.memory.add(para, source=path.name)
            n += 1
        print(f"✅ 已从 {path.name} 摄取 {n} 段记忆，当前共 {len(agent.memory.items)} 条。")

    elif args.cmd == "face":
        src = pathlib.Path(args.image)
        if not src.exists():
            raise SystemExit(f"找不到图片：{src}")
        faces = BASE / "data" / "faces"
        faces.mkdir(parents=True, exist_ok=True)
        dst = faces / (args.face_id + src.suffix.lower())
        shutil.copy(src, dst)
        print(f"✅ 已登记人脸：{args.face_id} -> {dst}")
        print("   记得在 config/relationships.yaml 里把某个人的 face_id 设为同名。")


if __name__ == "__main__":
    main()
