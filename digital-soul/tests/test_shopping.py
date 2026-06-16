"""采买清单测试。可直接运行：python tests/test_shopping.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.shopping import ShoppingList  # noqa: E402


def test_add_checkoff_remove_persist():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "s.json"
        s = ShoppingList(p)
        assert s.add("") is None
        s.add("酱油", qty=1)
        s.add("鸡蛋", qty=12)
        assert len(s.pending()) == 2
        s.add("酱油", qty=2)                       # 同名更新数量，不新增
        assert len(s.items) == 2 and s.items[0]["qty"] == 2
        assert s.check_off("鸡蛋")["done"] is True
        assert len(s.pending()) == 1
        assert s.remove("酱油") is True and s.remove("不存在") is False
        assert ShoppingList(p).items == s.items     # 持久化


def test_describe_and_clear():
    with tempfile.TemporaryDirectory() as d:
        s = ShoppingList(pathlib.Path(d) / "s.json")
        assert "空的" in s.describe()
        s.add("牛奶", qty=2)
        assert "牛奶×2" in s.describe()
        assert s.clear() == 1 and "空的" in s.describe()


def test_agent_shop_flow():
    a = object.__new__(Agent)
    with tempfile.TemporaryDirectory() as d:
        a.shopping = ShoppingList(pathlib.Path(d) / "s.json")
        assert "酱油" in a.shop_add("酱油")
        assert "牛奶" in a.shop_list() or "酱油" in a.shop_list()
        assert "划掉" in a.shop_done("酱油")
        assert "没找到" in a.shop_done("不存在的")
    a.shopping = None
    assert a.shop_add("x") == "" and a.shop_list() == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ shopping: all tests passed")
