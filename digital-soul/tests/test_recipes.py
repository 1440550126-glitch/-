"""家传菜谱测试。可直接运行：python tests/test_recipes.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.recipes import (collect_recipes, find_recipe,  # noqa: E402
                           list_names, recipe_text)

CFG = {"recipes": [
    {"name": "红烧肉", "by": "外婆", "ingredients": ["五花肉", "冰糖"],
     "steps": ["焯水", "炒糖色"], "note": "小火"},
    {"name": "西红柿鸡蛋", "ingredients": ["西红柿", "鸡蛋"], "steps": ["炒蛋", "炒番茄"]},
]}
FAMILY = {"members": [{"name": "外公", "recipes": [{"name": "腊肉", "steps": ["腌", "晾"]}]}]}


def test_collect_merges_config_and_family():
    rs = collect_recipes(CFG, FAMILY)
    names = list_names(rs)
    assert "红烧肉" in names and "腊肉" in names
    laro = find_recipe(rs, "腊肉怎么做")
    assert laro["by"] == "外公"                     # 家人的菜自动标注 by


def test_find_and_text():
    rs = collect_recipes(CFG)
    r = find_recipe(rs, "晚上想吃红烧肉")
    t = recipe_text(r)
    assert "外婆的红烧肉" in t and "五花肉" in t and "1.焯水" in t and "诀窍：小火" in t
    assert find_recipe(rs, "佛跳墙") is None


def test_skips_invalid():
    rs = collect_recipes({"recipes": [{"no_name": 1}, "x", {"name": "蛋炒饭"}]})
    assert list_names(rs) == ["蛋炒饭"]


def test_agent_cook_and_list():
    a = object.__new__(Agent)
    a.recipes = CFG
    a.family = {}
    assert "外婆的红烧肉" in a.cook("红烧肉怎么做")
    assert "红烧肉" in a.cook("你有什么拿手菜") and "想吃哪个" in a.cook("你有什么拿手菜")
    assert a.cook("佛跳墙怎么做") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ recipes: all tests passed")
