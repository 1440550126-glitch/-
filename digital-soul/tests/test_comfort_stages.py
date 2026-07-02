"""哀伤阶段陪伴测试。可直接运行：python tests/test_comfort_stages.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.comfort_stages import (comfort_by_stage, days_between,  # noqa: E402
                                  stage_for)


def test_stage_for_buckets():
    assert stage_for(5) == "初痛"
    assert stage_for(60) == "浓念"
    assert stage_for(200) == "渐和"
    assert stage_for(500) == "长念"
    assert stage_for(None) == "" and stage_for(-1) == ""


def test_comfort_by_stage_text_and_name():
    assert "陪着你" in comfort_by_stage(5)
    assert comfort_by_stage(500).startswith("时间久了") or "温柔" in comfort_by_stage(500)
    assert comfort_by_stage(5, "小婷").startswith("小婷，")
    assert comfort_by_stage(None) == ""


def test_days_between():
    now = datetime(2024, 1, 1, 12)
    assert days_between("2023-12-22", now) == 10
    assert days_between("乱", now) is None
    assert days_between(None, now) is None


def test_agent_grief_stage_line():
    a = object.__new__(Agent)
    a.legacy = {"passed_on": "2023-09-15"}
    a.memorial = {}
    line = a.grief_stage_line("小婷", now=datetime(2023, 9, 20))
    assert line.startswith("小婷，") and "陪着你" in line
    a.legacy = {}                                   # 没配离开日期 → 不强行说
    assert a.grief_stage_line(now=datetime(2024, 1, 1)) == ""


def test_agent_passed_on_from_memorial():
    a = object.__new__(Agent)
    a.legacy = {}
    a.memorial = {"dates": {"外公的忌日": "2020-04-05"}}
    assert a._passed_on_date() == "2020-04-05"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ comfort_stages: all tests passed")
