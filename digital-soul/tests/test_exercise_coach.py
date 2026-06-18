"""动一动 / 养生操测试。可直接运行：python tests/test_exercise_coach.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.exercise_coach import (  # noqa: E402
    find_routine, guide, is_exercise_query, routines, suggest,
)


def test_routines():
    assert "散步" in routines() and "八段锦" in routines()


def test_find_routine():
    assert find_routine("脖子酸，教我护颈") == "护颈"
    assert find_routine("带我做八段锦") == "八段锦"
    assert find_routine("今天天气好") is None


def test_guide_steps():
    g = guide("护颈")
    assert "护颈" in g and "1）" in g and "舒服就好" in g
    assert guide("不存在") == ""


def test_suggest_by_time():
    assert "散步" in suggest(datetime(2026, 6, 18, 13))      # 饭点后散步
    assert "护颈" in suggest(datetime(2026, 6, 18, 10))      # 工作时间护颈


def test_is_exercise_query():
    assert is_exercise_query("陪我活动活动")
    assert is_exercise_query("带我做个操")
    assert not is_exercise_query("几点了")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ exercise_coach: all tests passed")
