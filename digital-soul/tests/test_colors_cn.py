"""中国传统色测试。可直接运行：python tests/test_colors_cn.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.colors_cn import (  # noqa: E402
    about,
    colors,
    find_color,
    is_color_query,
)


def test_colors_cover():
    cs = colors()
    for c in ("月白", "天青", "黛", "胭脂"):
        assert c in cs


def test_about():
    assert "月光" in about("月白")
    assert "汝窑" in about("天青") or "天晴" in about("天青")
    assert about("荧光绿") == ""


def test_find_color_alias_longest():
    assert find_color("天青是什么颜色") == "天青"
    assert find_color("眉黛是啥") == "黛"               # 别名
    assert find_color("今天天气") == ""


def test_about_from_sentence():
    assert "画眉" in about("黛是什么颜色") or "青黑" in about("黛是什么颜色")


def test_is_color_query():
    assert is_color_query("天青是什么颜色")
    assert is_color_query("中国传统色有哪些")
    assert is_color_query("胭脂是啥颜色")
    assert not is_color_query("今天几号")
    assert not is_color_query("我喜欢月白")              # 没问颜色


def test_config_add():
    cfg = {"colors": {"竹月": "淡淡的蓝绿，雅致清凉。"}}
    assert "竹月" in colors(cfg)
    assert "清凉" in about("竹月是什么颜色", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ colors_cn: all tests passed")
