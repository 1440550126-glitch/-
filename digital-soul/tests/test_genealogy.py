"""家谱 / 家族树测试。可直接运行：python tests/test_genealogy.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.genealogy import (  # noqa: E402
    birthday_line, build_tree, by_generation, roster_by_gen,
    upcoming_birthdays,
)

FAM = {"members": [
    {"name": "外公", "relation": "外公", "birthday": "1948-08-12"},
    {"name": "小明", "relation": "孙子", "birthday": "2015-06-20"},
    {"name": "妈妈", "relation": "母亲", "birthday": "1975-03-03"},
    {"name": "我", "relation": "本人", "gen": 0},
]}


def test_build_tree_sorts_by_generation():
    tree = build_tree(FAM)
    gens = [m["gen"] for m in tree]
    assert gens == sorted(gens)                           # 已按辈分升序
    assert tree[0]["name"] == "外公"                      # 祖辈在最前(-2)
    assert tree[-1]["name"] == "小明"                     # 孙辈在最后(+2)


def test_generation_inference():
    tree = build_tree(FAM)
    g = {m["name"]: m["gen"] for m in tree}
    assert g["外公"] == -2 and g["妈妈"] == -1
    assert g["我"] == 0 and g["小明"] == 2


def test_by_generation_groups():
    groups = dict(by_generation(build_tree(FAM)))
    assert groups["祖辈"] == ["外公"]
    assert groups["孙辈"] == ["小明"]


def test_roster_by_gen():
    s = roster_by_gen(build_tree(FAM))
    assert "祖辈：外公" in s and "孙辈：小明" in s
    assert roster_by_gen([]) == ""


def test_upcoming_birthdays():
    tree = build_tree(FAM)
    ups = upcoming_birthdays(tree, datetime(2026, 8, 10), within=30)
    assert ups[0] == ("外公", 2)                          # 8-10 → 8-12 还有 2 天
    line = birthday_line(tree, datetime(2026, 8, 12), within=30)
    assert "外公今天过生日" in line


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ genealogy: all tests passed")
