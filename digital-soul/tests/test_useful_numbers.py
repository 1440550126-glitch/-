"""常用号码测试。可直接运行：python tests/test_useful_numbers.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.useful_numbers import (  # noqa: E402
    all_numbers,
    emergency,
    is_number_query,
    number_for,
)


def test_all_numbers():
    items = all_numbers()
    nums = {num for _n, num, _w in items}
    for n in ("110", "119", "120", "96110"):
        assert n in nums


def test_emergency_line():
    e = emergency()
    assert "110" in e and "119" in e and "120" in e and "96110" in e


def test_number_for():
    assert "119" in number_for("着火了打哪个电话")
    assert "120" in number_for("有人晕倒了")
    assert "110" in number_for("有坏人要报警")
    assert "96110" in number_for("怀疑遇到诈骗")
    assert number_for("今天天气真好") == ""


def test_number_for_prefers_specific():
    # "车祸"应给 122 而不是泛泛 110
    assert "122" in number_for("出车祸了")


def test_is_number_query():
    assert is_number_query("报警电话是多少")
    assert is_number_query("着火打几")
    assert is_number_query("被骗了拨打什么号")
    assert not is_number_query("今天几号")
    assert not is_number_query("随便聊聊")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ useful_numbers: all tests passed")
