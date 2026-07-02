"""晨间关怀简报测试。可直接运行：python tests/test_briefing.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.briefing import compose_briefing, time_greeting  # noqa: E402


def test_time_greeting_buckets():
    assert time_greeting(datetime(2026, 6, 16, 7)) == "早上好"
    assert time_greeting(datetime(2026, 6, 16, 10)) == "上午好"
    assert time_greeting(datetime(2026, 6, 16, 13)) == "中午好"
    assert time_greeting(datetime(2026, 6, 16, 16)) == "下午好"
    assert time_greeting(datetime(2026, 6, 16, 20)) == "晚上好"
    assert time_greeting(datetime(2026, 6, 16, 2)) == "夜深了"


def test_compose_full():
    s = compose_briefing(
        name="小婷", occasions=["外公的忌日"], care=["该提醒妈吃降压药了"],
        agenda=["写周报", "陪妈散步"], last_words=["好好吃饭"],
        encouragement="今天也要好好的。", now=datetime(2026, 6, 16, 7))
    assert s.startswith("早上好，小婷。")
    assert "外公的忌日" in s and "「好好吃饭」" in s
    assert "该提醒妈吃降压药了" in s and "写周报" in s
    assert s.rstrip().endswith("今天也要好好的。")


def test_compose_skips_empty_blocks():
    s = compose_briefing(name="阿明", now=datetime(2026, 6, 16, 7))
    assert s == "早上好，阿明。 今天也要好好的。"      # 无日子/关照/计划 → 只问候+暖句
    assert "今天是" not in s and "惦记" not in s


def test_last_words_only_when_occasion():
    s = compose_briefing(care=["吃药"], last_words=["别太拼"], now=datetime(2026, 6, 16, 7))
    assert "别太拼" not in s                          # 没有纪念日，不郑重念遗言


def test_agent_care_briefing_end_to_end():
    a = object.__new__(Agent)
    a.care = {"妈": {"medicine": "08:00", "note": "降压药"}}
    a.memorial = {"dates": {}}
    a.legacy = {"last_words": ["好好吃饭"]}
    a.plan = type("P", (), {"items": [{"text": "陪妈散步", "status": "open"}]})()
    s = a.care_briefing(name="小婷", now=datetime(2026, 6, 16, 8, 0))
    assert "小婷" in s and "降压药" in s and "陪妈散步" in s


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ briefing: all tests passed")
