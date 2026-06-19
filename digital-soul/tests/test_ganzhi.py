"""天干地支测试。可直接运行：python tests/test_ganzhi.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.ganzhi import (  # noqa: E402
    animal_of,
    answer,
    describe,
    ganzhi_of,
    is_ganzhi_query,
    sexagenary,
)


def test_ganzhi_of_known():
    assert ganzhi_of(2026) == "丙午"
    assert ganzhi_of(1984) == "甲子"          # 甲子年
    assert ganzhi_of(2000) == "庚辰"


def test_animal_of():
    assert animal_of(2026) == "马"
    assert animal_of(1984) == "鼠"


def test_describe():
    s = describe(2026)
    assert "丙午" in s and "马" in s


def test_sexagenary():
    s = sexagenary()
    assert len(s) == 60
    assert s[0] == "甲子" and s[-1] == "癸亥"


def test_answer_with_year_and_relative():
    assert "丙午" in answer("2026年的干支是什么")
    a = answer("明年干支", now=datetime(2026, 6, 1))
    assert "丁未" in a                          # 2027 = 丁未


def test_is_ganzhi_query():
    assert is_ganzhi_query("2026年的天干地支")
    assert is_ganzhi_query("今年干支是什么")
    assert is_ganzhi_query("六十甲子")
    assert not is_ganzhi_query("今天几号")
    assert not is_ganzhi_query("我属马")          # 生肖归 zodiac


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ ganzhi: all tests passed")
