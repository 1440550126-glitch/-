"""行为习惯测试。可直接运行：python tests/test_habits.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.habits import current_activity  # noqa: E402

DAILY = [
    "早上一杯黑咖啡，刷会儿技术新闻",
    "白天写代码、开会、带团队",
    "晚饭后陪家人散步遛狗",
    "周末打打篮球，或者在家捣鼓开源项目",
]


def test_morning_activity():
    a = current_activity(DAILY, datetime(2024, 1, 1, 8, 0))   # 周一早上
    assert "咖啡" in a


def test_evening_activity():
    a = current_activity(DAILY, datetime(2024, 1, 1, 20, 0))  # 周一晚上
    assert "散步" in a or "陪家人" in a


def test_weekend_activity():
    a = current_activity(DAILY, datetime(2024, 1, 6, 15, 0))  # 周六
    assert "篮球" in a or "捣鼓" in a


def test_empty_daily():
    assert current_activity([], datetime(2024, 1, 1, 8, 0)) == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ habits: all tests passed")
