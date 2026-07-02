#!/usr/bin/env python3
"""自生长知识库 CLI：在命令行里给知识库添砖加瓦、看它长成什么样。

  python scripts/vault.py add 回锅肉 "川菜名菜，二刀肉先煮再炒" --tags 川菜,家常菜
  python scripts/vault.py add 川菜 "八大菜系之一，回锅肉麻婆豆腐都是川菜" --tags 菜系
  python scripts/vault.py capture "妈最拿手的就是 [[回锅肉]]，逢年过节必做" --tags 妈
  python scripts/vault.py find 回锅肉          # 看正文 + 反链 + 关联建议
  python scripts/vault.py list / stats / consolidate / index
  python scripts/vault.py demo                  # 撒几篇互相关联的笔记，演示"自生长"

默认库在 data/vault（和分身对话写的是同一座）；--root 换个目录。
写出来的就是标准 Obsidian markdown——直接用 Obsidian 打开 data/vault 就能看那张图谱。
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.knowledge_vault import Vault  # noqa: E402


def _csv(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description="自生长知识库（Claude × Obsidian）")
    ap.add_argument("--root", default="data/vault", help="知识库目录（默认 data/vault）")
    sub = ap.add_subparsers(dest="cmd")

    a = sub.add_parser("add", help="写一篇（已存在则并入）")
    a.add_argument("title"); a.add_argument("body", nargs="?", default="")
    a.add_argument("--tags", default=""); a.add_argument("--links", default="")

    c = sub.add_parser("capture", help="从一段话捕获成笔记")
    c.add_argument("text"); c.add_argument("--title", default=None); c.add_argument("--tags", default="")

    lk = sub.add_parser("link", help="连两篇"); lk.add_argument("a"); lk.add_argument("b")
    dn = sub.add_parser("daily", help="记进当天日记"); dn.add_argument("line")
    fd = sub.add_parser("find", help="看某篇 + 反链 + 建议"); fd.add_argument("title")
    sub.add_parser("list", help="列出所有笔记")
    sub.add_parser("stats", help="统计")
    sub.add_parser("consolidate", help="整理：孤岛/桩/关联建议")
    sub.add_parser("index", help="生成 _index.md 总览")
    sub.add_parser("demo", help="撒几篇互相关联的笔记演示自生长")

    args = ap.parse_args(argv)
    v = Vault(args.root)

    if args.cmd == "add":
        r = v.grow(args.title, args.body, tags=_csv(args.tags), links=_csv(args.links))
        print(f"{'新建' if r['created'] else '并入'}「{r['title']}」",
              f"自动连链 {r['auto_linked']}" if r.get("auto_linked") else "",
              f"建桩 {r['stubbed']}" if r.get("stubbed") else "")
    elif args.cmd == "capture":
        r = v.capture(args.text, title=args.title, tags=_csv(args.tags))
        print(f"捕获为「{r['title']}」 连上 {r.get('linked')}")
    elif args.cmd == "link":
        v.link(args.a, args.b); print(f"「{args.a}」↔「{args.b}」已连")
    elif args.cmd == "daily":
        print("记进", v.daily_note(args.line))
    elif args.cmd == "find":
        n = v.note(args.title)
        if not n:
            print("没有这篇"); return
        print(n["body"].strip()[:300])
        print("反链：", v.backlinks(args.title) or "—")
        print("建议关联：", v.suggest_links(args.title) or "—")
    elif args.cmd == "list":
        ts = v.titles()
        print(f"共 {len(ts)} 篇：", "、".join(ts) if ts else "（空）")
    elif args.cmd == "stats":
        print(v.stats())
    elif args.cmd == "consolidate":
        c = v.consolidate()
        print("统计：", c["stats"]); print("孤岛：", c["orphans"] or "—")
        print("待充实：", c["stubs"] or "—")
        for t, s in list(c["suggestions"].items())[:8]:
            print(f"  「{t}」也许连：{s}")
    elif args.cmd == "index":
        v.build_index(); print("已写", pathlib.Path(args.root) / "_index.md")
    elif args.cmd == "demo":
        seed = [
            ("数字分身", "一个本地优先的中文数字灵魂框架，目标 5 万行。会说话、有表情、能控制面部舵机，还有这座自生长知识库。", "项目,AI", ""),
            ("自生长知识库", "分身把学到的写成 Obsidian 笔记、自动连成图谱。属于 [[数字分身]] 的记忆外化。", "项目,知识管理", ""),
            ("面部舵机", "把表情变成舵机脉宽驱动机器人的脸，配合视觉闭环自我修正。也是 [[数字分身]] 的一部分。", "机器人", ""),
            ("Obsidian", "本地优先的 markdown 笔记软件，用 [[双链]] 连成知识图谱。", "工具,知识管理", ""),
        ]
        for t, b, tags, links in seed:
            r = v.grow(t, b, tags=_csv(tags), links=_csv(links))
            print(f"  +「{r['title']}」")
        v.build_index()
        print("撒好了。stats：", v.stats(), "\n用 Obsidian 打开", args.root, "看那张图谱。")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
