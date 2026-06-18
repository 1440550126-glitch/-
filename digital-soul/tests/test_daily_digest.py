"""今天提要测试。可直接运行：python tests/test_daily_digest.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.daily_digest import compose, gather, morning_digest  # noqa: E402


def test_compose_orders_and_joins():
    parts = {"festival": "今天是端午", "weather": "天凉加衣", "meds": "该吃降压药",
             "chores": "今天的分工：小明—买菜"}
    s = compose(parts, greeting="早呀，")
    assert s.startswith("早呀，")
    assert s.index("端午") < s.index("天凉") < s.index("降压药")   # 节日→天气→药 的顺序
    assert "今天的分工" in s and s.index("降压药") < s.index("分工")  # 药后接分工


def test_compose_empty():
    s = compose({}, greeting="早呀，")
    assert "没什么特别要紧" in s


def test_gather_degrades_on_bare_agent():
    bare = object.__new__(Agent)
    d = gather(bare, datetime(2026, 6, 18))           # 缺各种字段也不该炸
    assert isinstance(d, dict)
    # 依赖外部数据的块都为空（养生贴士只看日期，可非空）
    for k in ("meds", "appts", "plants", "touch", "habits", "weather"):
        assert d[k] == "", k


def test_gather_and_morning_digest():
    a = object.__new__(Agent)
    a.sensors = {"temperature": 5}
    a.family = {"members": [{"name": "小明", "relation": "孙子", "birthday": "06-19"}]}
    a.spouse = {}
    a.medications = None
    a.appointments = None
    a.plants = None
    a.touch = None
    a.habits_book = None
    a.memorial = {}
    a.calendar = None
    s = morning_digest(a, now=datetime(2026, 6, 18), greeting="早呀，")
    assert "早呀，" in s
    assert "加衣" in s or "厚" in s                    # 天冷穿衣
    assert "小明" in s                                 # 明天孙子生日


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ daily_digest: all tests passed")
