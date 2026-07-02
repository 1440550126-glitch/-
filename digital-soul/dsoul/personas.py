"""人格切换的共享逻辑：列出 / 套用 config/examples 模板。

被 scripts/persona.py（命令行）和 Agent.switch_persona（运行时热切换）复用。
"""

from __future__ import annotations

import pathlib
import shutil
import time

import yaml

# 这些人设默认套用"恋人/陪伴"关系（你 = 被爱、被守护的人）
COMPANION = {
    "doting-boyfriend", "ceo-boyfriend", "gentle-girlfriend", "flirty-girlfriend",
    "flirty-boyfriend", "tsundere", "yandere", "mature-onee", "sunshine-boy",
    "elite-senior", "loyal-knight", "scheming", "cold-assassin",
}


def _base(base_dir=None) -> pathlib.Path:
    return pathlib.Path(base_dir) if base_dir else pathlib.Path(__file__).resolve().parent.parent


def list_personas(base_dir=None) -> dict:
    ex = _base(base_dir) / "config" / "examples"
    out = {}
    for f in sorted(ex.glob("identity.*.yaml")):
        name = f.name[len("identity."):-len(".yaml")]
        try:
            d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        except Exception:
            d = {}
        out[name] = d.get("summary", "")
    return out


def current_name(base_dir=None) -> str:
    p = _base(base_dir) / "config" / "identity.yaml"
    if p.exists():
        d = yaml.safe_load(open(p, encoding="utf-8")) or {}
        return d.get("name", "?")
    return "（未设置）"


def apply_persona(name, base_dir=None, keep_relationships=False, seed_memory=False) -> dict:
    base = _base(base_dir)
    ex = base / "config" / "examples"
    cfg = base / "config"
    src_id = ex / f"identity.{name}.yaml"
    if not src_id.exists():
        raise ValueError(f"没有这个人格：{name}")

    changed = []
    shutil.copy(src_id, cfg / "identity.yaml")
    changed.append(f"身份 → {name}")

    if name in COMPANION and not keep_relationships:
        shutil.copy(ex / "relationships.companion.yaml", cfg / "relationships.yaml")
        changed.append("关系 → 恋人/陪伴（你 = 被爱、被守护的人）")

    if seed_memory:
        seed = ex / "memories" / f"{name}.md"
        src = base / "data" / "memories" / "sources"
        idx = base / "data" / "memories" / "index.json"
        if seed.exists():
            src.mkdir(parents=True, exist_ok=True)
            olds = list(src.glob("*.md")) + list(src.glob("*.txt"))
            if olds:  # 先备份你的真实记忆，绝不直接删
                bak = src.parent / f"sources_backup_{int(time.time())}"
                bak.mkdir(parents=True, exist_ok=True)
                for o in olds:
                    shutil.move(str(o), str(bak / o.name))
                changed.append(f"旧记忆已备份到 {bak.name}/")
            shutil.copy(seed, src / f"{name}.md")
            if idx.exists():
                idx.unlink()
            changed.append("记忆 → 这套人设的'我们的故事'（已重置）")
        else:
            changed.append("（暂无专属记忆，记忆未改动）")

    return {"name": name, "changed": changed, "companion": name in COMPANION}
