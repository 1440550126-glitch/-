"""临别期许测试。可直接运行：python tests/test_wishes.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.wishes import all_wishes, collect_wishes, wish_for  # noqa: E402


def test_collect_merges_legacy_and_family():
    legacy = {"wishes": {"小婷": "对自己好点"}}
    family = {"members": [{"name": "外公", "wish": "踏实做人"},
                          {"name": "小婷", "wish": "（被 legacy 覆盖）"}]}
    w = collect_wishes(legacy, family)
    assert w["小婷"] == "对自己好点"          # legacy 优先
    assert w["外公"] == "踏实做人"


def test_wish_for_exact_and_fuzzy():
    w = {"小婷": "别太省", "孩子": "走正道"}
    assert wish_for(w, "小婷") == "别太省"
    assert wish_for(w, "我的孩子") == "走正道"   # 模糊包含
    assert wish_for(w, "陌生人") is None
    assert wish_for(w, None) is None


def test_all_wishes_lines():
    assert all_wishes({"小婷": "别太省"}) == ["对小婷：别太省"]
    assert all_wishes({}) == []


def test_agent_deliver_wish():
    a = object.__new__(Agent)
    a.identity = {"name": "张明", "personality": {}}
    a.legacy = {"wishes": {"小婷": "别太省，对自己好点"}}
    a.family = {}
    s = a.deliver_wish("小婷")
    assert "别太省" in s
    assert a.deliver_wish("陌生人") == ""        # 没配就不硬编


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ wishes: all tests passed")
