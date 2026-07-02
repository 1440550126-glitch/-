"""垃圾分类测试。可直接运行：python tests/test_garbage_sort.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.garbage_sort import (  # noqa: E402
    categories,
    find_item,
    is_sort_query,
    sort,
)


def test_categories():
    cs = categories()
    assert any("厨余" in c for c in cs)
    assert any("有害" in c for c in cs)
    assert len(cs) == 4


def test_sort_basic():
    assert "厨余" in sort("西瓜皮")
    assert "有害" in sort("过期药")
    assert "可回收" in sort("塑料瓶")
    assert "其他" in sort("烟头")


def test_sort_unknown_empty():
    assert sort("外星飞船") == ""


def test_find_item_longest_and_alias():
    assert find_item("废电池是什么垃圾") == "电池"
    assert find_item("可乐瓶咋扔") == "塑料瓶"        # 别名
    assert find_item("今天天气") == ""


def test_sort_from_sentence():
    assert "厨余" in sort("西瓜皮是什么垃圾")


def test_is_sort_query():
    assert is_sort_query("电池是什么垃圾")
    assert is_sort_query("垃圾分类怎么分")
    assert is_sort_query("过期药怎么扔")
    assert not is_sort_query("今天几号")
    # 提到"什么垃圾"但没具体东西，仍允许（泛问分类）——这里给具体东西更稳
    assert is_sort_query("塑料瓶归哪类")


def test_config_override():
    cfg = {"garbage": {"小龙虾壳": "其他"}}             # 各地不同，本地可改
    assert "其他" in sort("小龙虾壳", cfg)
    assert find_item("小龙虾壳怎么扔", cfg) == "小龙虾壳"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ garbage_sort: all tests passed")
