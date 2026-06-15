#!/usr/bin/env python3
"""一键切换人格：把 config/examples 里的模板套用到当前配置。

  digital-soul persona                       # 列出所有人格 + 当前身份
  digital-soul persona flirty-girlfriend     # 切到"色色女友"（恋人类会同时套用配套关系）
  digital-soul persona gentle-mom --keep-relationships    # 不动关系配置
  digital-soul persona flirty-girlfriend --seed-memory    # 同时换上这套"我们的故事"(会先备份旧记忆)
"""

import argparse
import pathlib
import shutil
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent
EX = BASE / "config" / "examples"
CFG = BASE / "config"
SRC = BASE / "data" / "memories" / "sources"
IDX = BASE / "data" / "memories" / "index.json"

# 这些人设默认套用"恋人/陪伴"关系（你=被爱、被守护的人）
COMPANION = {
    "doting-boyfriend", "ceo-boyfriend", "gentle-girlfriend", "flirty-girlfriend",
    "flirty-boyfriend", "tsundere", "yandere", "mature-onee", "sunshine-boy",
    "elite-senior", "loyal-knight", "scheming", "cold-assassin",
}


def _available() -> dict:
    out = {}
    for f in sorted(EX.glob("identity.*.yaml")):
        name = f.name[len("identity."):-len(".yaml")]
        try:
            d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        except Exception:
            d = {}
        out[name] = d.get("summary", "")
    return out


def _current() -> str:
    p = CFG / "identity.yaml"
    if p.exists():
        d = yaml.safe_load(open(p, encoding="utf-8")) or {}
        return d.get("name", "?")
    return "（未设置）"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", help="人格名（不填则列出全部）")
    ap.add_argument("--keep-relationships", action="store_true", help="不替换关系配置")
    ap.add_argument("--seed-memory", action="store_true", help="同时换上该人设的示例记忆（会先备份旧记忆）")
    args = ap.parse_args()

    av = _available()
    if not args.name:
        print(f"当前身份：{_current()}\n")
        print("可用人格（digital-soul persona <名字>）：")
        for n, s in av.items():
            tag = "💕" if n in COMPANION else "👪"
            print(f"  {tag} {n.ljust(18)} {s[:34]}")
        return

    if args.name not in av:
        print(f"没有这个人格：{args.name}\n可用：{', '.join(av)}")
        sys.exit(2)

    done = []
    shutil.copy(EX / f"identity.{args.name}.yaml", CFG / "identity.yaml")
    done.append(f"身份 → {args.name}（{_current()}）")

    if args.name in COMPANION and not args.keep_relationships:
        shutil.copy(EX / "relationships.companion.yaml", CFG / "relationships.yaml")
        done.append("关系 → 恋人/陪伴（你 = 被爱、被守护的人）")

    if args.seed_memory:
        seed = EX / "memories" / f"{args.name}.md"
        if seed.exists():
            SRC.mkdir(parents=True, exist_ok=True)
            olds = list(SRC.glob("*.md")) + list(SRC.glob("*.txt"))
            if olds:  # 先备份你的真实记忆源，绝不直接删
                bak = SRC.parent / f"sources_backup_{int(time.time())}"
                bak.mkdir(parents=True, exist_ok=True)
                for o in olds:
                    shutil.move(str(o), str(bak / o.name))
                done.append(f"旧记忆已备份到 {bak.relative_to(BASE)}/")
            shutil.copy(seed, SRC / f"{args.name}.md")
            if IDX.exists():
                IDX.unlink()
            done.append("记忆 → 这套人设的'我们的故事'（已重置）")
        else:
            done.append(f"（暂无 {args.name} 的示例记忆，记忆未改动）")

    print("✅ 已切换：")
    for d in done:
        print("   -", d)
    print("\n试试：digital-soul chat   或   digital-soul demo")


if __name__ == "__main__":
    main()
