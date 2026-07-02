"""家传菜谱：记下 TA 的拿手菜与做法，谁问"外婆的红烧肉怎么做"都能照着来。

配在 config/recipes.yaml（一组菜），或 family 成员的 recipes 字段。
纯逻辑、零依赖、可单测；只做查找与排版，不联网。
"""

from __future__ import annotations


def _norm(recipes) -> list:
    """规整成 [{name, by, ingredients, steps, note}, …]，跳过没名字的。"""
    out = []
    src = recipes.get("recipes", recipes) if isinstance(recipes, dict) else recipes
    for r in (src or []):
        if isinstance(r, dict) and r.get("name"):
            out.append(r)
    return out


def collect_recipes(recipes=None, family=None) -> list:
    """汇总：config 菜谱 + 各家人 recipes 字段（标注 by=家人名）。"""
    out = _norm(recipes or {})
    try:
        from .family import members
        for m in members(family or {}):
            for r in (m.get("recipes") or []):
                if isinstance(r, dict) and r.get("name"):
                    out.append({**r, "by": r.get("by", m["name"])})
    except Exception:
        pass
    return out


def find_recipe(recipes, query) -> dict | None:
    if not query:
        return None
    q = str(query)
    for r in recipes:
        if r["name"] and r["name"] in q:
            return r
    return None


def recipe_text(r) -> str:
    """把一道菜排成"谁的拿手菜 + 用料 + 步骤 + 一句叮嘱"。"""
    if not r:
        return ""
    by = r.get("by")
    head = f"{by}的{r['name']}" if by else r["name"]
    L = [f"【{head}】"]
    ing = r.get("ingredients") or []
    if ing:
        L.append("用料：" + "、".join(str(x) for x in ing))
    steps = r.get("steps") or []
    if steps:
        L.append("做法：" + "；".join(f"{i}.{s}" for i, s in enumerate(steps, 1)))
    if r.get("note"):
        L.append("诀窍：" + str(r["note"]))
    return "\n".join(L)


def list_names(recipes) -> list:
    return [r["name"] for r in recipes if r.get("name")]
