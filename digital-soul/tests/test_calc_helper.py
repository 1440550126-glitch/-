"""生活小计算测试。可直接运行：python tests/test_calc_helper.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.calc_helper import (  # noqa: E402
    answer,
    bmi,
    discount,
    is_calc_query,
    parse_bmi,
    parse_discount,
)


def test_discount():
    assert discount(100, 8) == 80
    assert discount(100, 8.5) == 85
    assert discount(199, 5) == 99.5


def test_parse_discount():
    s = parse_discount("100块打8折是多少")
    assert "80" in s and "省" in s
    assert "85" in parse_discount("原价100打8.5折")
    assert parse_discount("今天天气") == ""


def test_bmi():
    v, cat = bmi(170, 65)
    assert v == 22.5 and "正常" in cat
    v2, cat2 = bmi(1.7, 65)                          # 米也认
    assert v2 == 22.5
    v3, _ = bmi(170, 90)
    assert v3 > 28


def test_parse_bmi():
    s = parse_bmi("身高170体重65")
    assert "22.5" in s
    s2 = parse_bmi("身高1.7米 体重130斤")             # 市斤换算
    assert "22.5" in s2
    assert parse_bmi("今天几号") == ""


def test_is_calc_query():
    assert is_calc_query("100打8折是多少")
    assert is_calc_query("身高170体重65 BMI是多少")
    assert not is_calc_query("今天几号")
    assert not is_calc_query("二加七等于几")           # 普通算术归日常问答


def test_answer_routes():
    assert "80" in answer("100块打8折")
    assert "22.5" in answer("身高170体重65")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ calc_helper: all tests passed")
