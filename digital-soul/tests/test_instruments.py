"""认民族乐器测试。可直接运行：python tests/test_instruments.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.instruments import (  # noqa: E402
    about,
    find_instrument,
    instruments,
    is_instrument_query,
)


def test_instruments_cover():
    its = instruments()
    for x in ("二胡", "古筝", "琵琶", "笛子"):
        assert x in its


def test_about():
    assert "二泉映月" in about("二胡")
    assert "十面埋伏" in about("琵琶")
    assert about("电吉他") == ""


def test_find_alias_longest():
    assert find_instrument("胡琴是什么乐器") == "二胡"   # 别名
    assert find_instrument("竹笛好听吗") == "笛子"
    assert find_instrument("今天天气") == ""


def test_about_from_sentence():
    assert "渔舟唱晚" in about("古筝有什么名曲")


def test_is_instrument_query():
    assert is_instrument_query("二胡是什么乐器")
    assert is_instrument_query("民族乐器有哪些")
    assert is_instrument_query("琵琶名曲")
    assert not is_instrument_query("今天几号")
    assert not is_instrument_query("我会拉二胡")          # 没问介绍/音色/名曲


def test_config_add():
    cfg = {"instruments": {"马头琴": ["蒙古族拉弦乐器", "苍凉辽阔", "《万马奔腾》"]}}
    assert "马头琴" in instruments(cfg)
    assert "万马奔腾" in about("马头琴是什么乐器", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ instruments: all tests passed")
