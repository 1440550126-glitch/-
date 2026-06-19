"""家常菜手把手测试。可直接运行：python tests/test_home_cooking.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.home_cooking import (  # noqa: E402
    dishes,
    find,
    how_to,
    is_cooking_howto,
)


def test_dishes_cover():
    ds = dishes()
    for d in ("西红柿炒蛋", "红烧肉", "蛋炒饭", "清蒸鱼"):
        assert d in ds


def test_find_and_alias():
    assert find("西红柿炒蛋怎么做") == "西红柿炒蛋"
    assert find("番茄炒蛋咋整") == "西红柿炒蛋"     # 别名
    assert find("教我做红烧肉") == "红烧肉"
    assert find("今天天气") == ""


def test_how_to_format():
    s = how_to("红烧肉")
    assert "用料：" in s and "做法：" in s and "窍门：" in s
    assert "1." in s and "焯" in s


def test_how_to_by_sentence():
    s = how_to("可乐鸡翅怎么做")
    assert "可乐" in s and "做法" in s


def test_how_to_unknown_empty():
    assert how_to("佛跳墙") == ""


def test_is_cooking_howto():
    assert is_cooking_howto("西红柿炒蛋怎么做")
    assert is_cooking_howto("教我做红烧肉")
    assert not is_cooking_howto("红烧肉好吃吗")     # 没问做法
    assert not is_cooking_howto("今天几号")


def test_config_adds_dish():
    cfg = {"home_cooking": {"奶奶的扣肉": {"用料": "五花肉、梅干菜",
                                          "步骤": ["蒸", "扣"], "窍门": "蒸够火候"}}}
    assert "奶奶的扣肉" in dishes(cfg)
    s = how_to("奶奶的扣肉", cfg)
    assert "梅干菜" in s and "蒸够火候" in s
    assert is_cooking_howto("奶奶的扣肉怎么做", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ home_cooking: all tests passed")
