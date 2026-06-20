"""单位换算测试。可直接运行：python tests/test_unit_convert.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.unit_convert import (  # noqa: E402
    answer, convert, count, is_convert_query, parse_query,
)


def test_count_units():
    assert count() >= 40


def test_convert_weight_length_area():
    assert convert(3, "斤", "克") == 1500
    assert convert(1, "公斤", "斤") == 2
    assert convert(10, "里", "米") == 5000
    assert abs(convert(1, "亩", "平方米") - 666.6667) < 0.01


def test_convert_temperature():
    assert abs(convert(100, "华氏", "摄氏") - 37.7778) < 0.01
    assert abs(convert(37, "摄氏", "华氏") - 98.6) < 0.01
    assert convert(0, "摄氏", "华氏") == 32


def test_convert_errors():
    try:
        convert(1, "斤", "米")            # 跨维度
        assert False
    except ValueError:
        pass
    try:
        convert(1, "摄氏", "斤")          # 温度 vs 重量
        assert False
    except ValueError:
        pass


def test_parse_query_number_and_units():
    assert parse_query("3斤是多少克") == (3.0, "斤", "克")
    assert parse_query("一亩等于多少平方米") == (1.0, "亩", "平方米")
    # "两公斤"里的"两"是数字 2，不是单位两
    assert parse_query("两公斤等于多少斤") == (2.0, "公斤", "斤")
    assert parse_query("半斤多少两") == (0.5, "斤", "两")
    assert parse_query("今天天气好") is None     # 没有可换算的单位对


def test_answer_formats():
    assert answer("3斤是多少克") == "3斤 ≈ 1500克。"
    assert answer("1公斤是多少斤") == "1公斤 ≈ 2斤。"
    assert answer("5公里是几里") == "5公里 ≈ 10里。"
    # 温度带「度」，且不重复
    a = answer("100华氏度是多少摄氏度")
    assert "华氏度度" not in a and "摄氏度" in a and "37.7" in a
    assert answer("今天天气好") == ""


def test_is_convert_query_gating():
    assert is_convert_query("一斤等于多少克")
    assert is_convert_query("两公斤是几斤")
    assert not is_convert_query("今天天气好")
    assert not is_convert_query("我想吃三斤橘子")      # 有单位但没换算意图（没问多少/等于）


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ unit_convert: all tests passed")
