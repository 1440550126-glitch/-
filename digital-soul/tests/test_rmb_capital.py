"""人民币金额大写测试。可直接运行：python tests/test_rmb_capital.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.rmb_capital import (  # noqa: E402
    answer, find_amount, is_capital_query, to_capital,
)


def test_whole_yuan():
    assert to_capital(0) == "零元整"
    assert to_capital(5) == "伍元整"
    assert to_capital(100) == "壹佰元整"
    assert to_capital(1250) == "壹仟贰佰伍拾元整"
    assert to_capital(10000) == "壹万元整"
    assert to_capital(1000000) == "壹佰万元整"
    assert to_capital(100000000) == "壹亿元整"


def test_zero_handling():
    assert to_capital(105) == "壹佰零伍元整"
    assert to_capital(10001) == "壹万零壹元整"
    assert to_capital(20100) == "贰万零壹佰元整"


def test_jiao_fen():
    assert to_capital(1250.5) == "壹仟贰佰伍拾元伍角整"      # 有角无分 → 整
    assert to_capital(1250.05) == "壹仟贰佰伍拾元零伍分"     # 无角有分 → 零X分
    assert to_capital(1250.55) == "壹仟贰佰伍拾元伍角伍分"
    assert to_capital(1000.4) == "壹仟元肆角整"
    assert to_capital(0.5) == "伍角整"                       # 不足一元不写元
    assert to_capital(0.05) == "伍分"


def test_rounding_and_negative():
    assert to_capital(1.005) == "壹元零壹分"                 # 四舍五入到分
    assert to_capital(-88.8).startswith("负")
    assert to_capital("非数字") == ""


def test_find_amount():
    assert find_amount("1250.5元大写") == 1250.5
    assert find_amount("金额12,000大写") == 12000            # 去千分位逗号
    assert find_amount("没有数字") is None


def test_is_capital_query_gating():
    assert is_capital_query("1250.5元大写怎么写")
    assert is_capital_query("把3050块写成大写")
    assert not is_capital_query("今天天气好")
    assert not is_capital_query("大写一下")                  # 有"大写"但没钱/数字


def test_answer():
    assert "壹仟贰佰伍拾元伍角整" in answer("1250.5元大写怎么写")
    assert answer("今天天气好") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ rmb_capital: all tests passed")
