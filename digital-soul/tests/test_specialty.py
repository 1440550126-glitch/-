"""各地特产测试。可直接运行：python tests/test_specialty.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.specialty import (  # noqa: E402
    about,
    find_province,
    is_specialty_query,
    provinces,
)


def test_provinces_count():
    ps = provinces()
    assert len(ps) >= 30
    for p in ("北京", "云南", "四川", "广东", "新疆"):
        assert p in ps


def test_about():
    assert "烤鸭" in about("北京")
    assert "过桥米线" in about("云南")
    assert about("月球") == ""


def test_find_province_alias_and_longest():
    assert find_province("云南有什么特产") == "云南"
    assert find_province("成都有啥好吃的") == "四川"      # 城市别名
    assert find_province("滇菜") == "云南"                # 简称
    assert find_province("今天天气") == ""


def test_about_from_sentence():
    assert "螺蛳粉" in about("广西有什么特产")


def test_is_specialty_query():
    assert is_specialty_query("云南有什么特产")
    assert is_specialty_query("北京小吃有啥")
    assert is_specialty_query("四川有什么好玩的")
    assert not is_specialty_query("今天几号")
    assert not is_specialty_query("我去过云南")           # 没问特产


def test_config_add():
    cfg = {"specialty": {"老家村": "自家的腌菜和米酒。"}}
    assert "老家村" in provinces(cfg)
    assert "米酒" in about("老家村", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ specialty: all tests passed")
