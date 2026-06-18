"""二十四节气测试。可直接运行：python tests/test_solar_terms.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.solar_terms import (  # noqa: E402
    _TERMS, current_term, next_term, seasonal_wisdom, term_on, wisdom,
)


def test_twenty_four_terms():
    assert len(_TERMS) == 24                              # 二十四节气齐全
    names = [t[0] for t in _TERMS]
    assert "清明" in names and "冬至" in names and "立春" in names


def test_term_on_exact_day():
    t = term_on(datetime(2026, 4, 5))                     # 清明
    assert t and t[0] == "清明"
    assert term_on(datetime(2026, 4, 12), window=1) is None  # 离节气好几天


def test_current_term():
    # 4-10 处在清明(4-5)与谷雨(4-20)之间，当前节气是清明
    name, md, tip = current_term(datetime(2026, 4, 10))
    assert name == "清明"
    # 一月初还没到小寒(1-6)，回退到上一年的冬至
    assert current_term(datetime(2026, 1, 1))[0] == "冬至"


def test_wisdom_and_seasonal():
    assert "清明" in wisdom(("清明", "04-05", "去看看想念的人"))
    assert wisdom(None) == ""
    s = seasonal_wisdom(datetime(2026, 12, 23))           # 冬至刚过
    assert "冬至" in s


def test_next_term():
    name, left = next_term(datetime(2026, 4, 6))          # 清明刚过，下一个谷雨(4-20)
    assert name == "谷雨" and left == 14


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ solar_terms: all tests passed")
