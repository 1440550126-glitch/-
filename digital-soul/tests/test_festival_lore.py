"""节日吃食与来历测试。可直接运行：python tests/test_festival_lore.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.festival_lore import (  # noqa: E402
    detect, festivals, food_of, is_lore_query, lore,
)


def test_festivals_and_food():
    assert "端午" in festivals() and "中秋" in festivals()
    assert any("粽子" in x for x in food_of("端午"))
    assert any("月饼" in x for x in food_of("中秋"))


def test_detect():
    assert detect("端午吃什么") == "端午"
    assert detect("过年的来历") == "春节"
    assert detect("中秋节怎么来的") == "中秋"
    assert detect("今天几号") is None


def test_is_lore_query():
    assert is_lore_query("端午吃什么")
    assert is_lore_query("粽子的来历")
    assert not is_lore_query("现在几点")


def test_lore():
    t = lore("端午")
    assert "粽子" in t and "屈原" in t
    assert "团圆" in lore("中秋")
    assert lore("不存在") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ festival_lore: all tests passed")
