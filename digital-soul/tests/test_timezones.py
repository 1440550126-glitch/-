"""世界时间/时差测试。可直接运行：python tests/test_timezones.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.timezones import (  # noqa: E402
    answer, call_advice, count, diff_text, find_place, is_timezone_query,
    time_in,
)

# 固定一个"北京时间"，让结果可复现：2026-06-20（周六）20:00
NOW = datetime(2026, 6, 20, 20, 0)


def test_count_places():
    assert count() >= 30


def test_find_place_longest():
    assert find_place("纽约现在几点")[0] == "纽约"
    assert find_place("美西那边")[0] == "美国西部"
    assert find_place("今天天气好") is None


def test_diff_text():
    assert diff_text(8) == "和北京同一个时间"        # 新加坡
    assert "早" in diff_text(9)                       # 东京 +9
    assert "晚" in diff_text(-5)                      # 纽约 -5
    assert "半" in diff_text(5.5)                     # 印度 +5:30


def test_time_in_computes_right():
    # 北京 20:00 → 纽约(-5) 应是同日 07:00（差 13 小时）
    s = time_in("纽约", now=NOW)
    assert "07:00" in s and "晚" in s
    # 东京(+9) 比北京早 1 小时 → 21:00
    assert "21:00" in time_in("东京", now=NOW)
    # 新加坡(+8) 与北京同步 → 20:00
    assert "20:00" in time_in("新加坡", now=NOW)
    # 印度(+5.5) → 17:30
    assert "17:30" in time_in("印度", now=NOW)
    assert time_in("火星", now=NOW) == ""             # 不认识


def test_dst_note_present_or_absent():
    assert "夏令时" in time_in("纽约", now=NOW)        # 美国有夏令时 → 带提醒
    assert "夏令时" not in time_in("东京", now=NOW)    # 日本没有 → 不带


def test_call_advice_sleep_window():
    # 北京 20:00 → 洛杉矶(-8) 是凌晨 4:00，应提醒别打扰
    assert "睡" in call_advice("洛杉矶", now=NOW)
    # 东京 21:00 → 正常
    assert "正合适" in call_advice("东京", now=NOW)


def test_answer_combines():
    a = answer("孙子在纽约现在几点", now=NOW)
    assert "纽约现在是" in a and ("正合适" in a or "睡" in a)
    assert answer("今天天气好", now=NOW) == ""


def test_is_timezone_query_gating():
    assert is_timezone_query("纽约现在几点")
    assert is_timezone_query("北京和伦敦时差多少")
    assert not is_timezone_query("现在几点")           # 没外地地名 → 走本地报时
    assert not is_timezone_query("纽约挺好的")         # 有地名但不是问时间
    assert not is_timezone_query("今天天气好")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ timezones: all tests passed")
