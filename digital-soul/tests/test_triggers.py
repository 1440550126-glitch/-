"""自动化触发测试。可直接运行：python tests/test_triggers.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.authority import Authority  # noqa: E402
from dsoul.devices import DeviceHub  # noqa: E402
from dsoul.scenes import SceneBook  # noqa: E402
from dsoul.triggers import TriggerBook, parse_trigger  # noqa: E402


def test_parse_time_and_event():
    t1 = parse_trigger("每天22点提醒锁门", [])
    assert t1["kind"] == "time" and t1["spec"] == "22:00" and t1["action"]["type"] == "remind"
    t2 = parse_trigger("我一进门就开灯", [])
    assert t2["kind"] == "event" and t2["spec"] == "enter" and t2["action"]["type"] == "device"
    t3 = parse_trigger("每天18:30启动回家模式", ["回家模式"])
    assert t3["kind"] == "time" and t3["spec"] == "18:30" and t3["action"]["type"] == "scene"
    assert parse_trigger("今天天气不错", []) is None


def test_triggerbook_add_clear_persist():
    p = tempfile.mktemp(suffix=".json")
    tb = TriggerBook(p)
    tb.add(parse_trigger("每天22点提醒锁门", []))
    assert len(TriggerBook(p).all()) == 1          # 持久化
    assert tb.clear() == 1 and tb.all() == []


def _agent():
    rel = {"permissions": {"owner": ["*"], "stranger": []},
           "people": [{"name": "张明", "relation": "本人", "trust": "owner"},
                      {"name": "路人", "relation": "陌生人", "trust": "stranger"}]}
    a = object.__new__(Agent)
    a.authority = Authority(rel)
    a.devices = DeviceHub()
    a.scenes = SceneBook()
    a.triggers = TriggerBook(tempfile.mktemp(suffix=".json"))
    a._sun_times = {"sunrise": "06:30", "sunset": "18:30"}
    a.sensors = {"temperature": 22}
    return a


def test_time_trigger_fires_once_per_day():
    a = _agent()
    a._trigger_route("张明", "每天22点开灯")
    assert a.check_time_triggers(datetime(2026, 1, 1, 21, 0)) == []     # 没到点
    fired = a.check_time_triggers(datetime(2026, 1, 1, 22, 0))
    assert fired and a.devices.states()["light"]["power"] == "on"
    assert a.check_time_triggers(datetime(2026, 1, 1, 22, 0)) == []     # 当天只触发一次


def test_event_trigger_on_enter_and_auth():
    a = _agent()
    a._trigger_route("张明", "我一进门就开灯")
    assert a.fire_event("enter", "张明")                                # 进门 → 开灯
    assert a.devices.states()["light"]["power"] == "on"
    # 陌生人不能设定自动化
    assert "不会听" in a._trigger_route("路人", "每天22点开灯")


def test_parse_weekly_sun_condition():
    assert parse_trigger("每周一22点开灯", [])["days"] == [0]
    assert parse_trigger("工作日7点开灯", [])["days"] == [0, 1, 2, 3, 4]
    assert parse_trigger("日落时开灯", [])["spec"] == "sunset"
    c = parse_trigger("温度低于18就开空调", [])
    assert c["kind"] == "cond" and c["spec"] == {"sensor": "temperature", "op": "<", "value": 18}


def test_weekly_day_filter():
    a = _agent()
    a._trigger_route("张明", "每周一22点开灯")
    tue, mon = datetime(2024, 1, 2, 22, 0), datetime(2024, 1, 1, 22, 0)   # 周二 / 周一
    assert a.check_time_triggers(tue) == []          # 周二不触发
    assert a.check_time_triggers(mon)                # 周一触发


def test_sunset_resolves_to_time():
    a = _agent()
    a._trigger_route("张明", "日落时开灯")
    assert a.check_time_triggers(datetime(2024, 1, 1, 18, 30))   # 默认日落 18:30
    assert a.devices.states()["light"]["power"] == "on"


def test_condition_rising_edge_fires_once():
    a = _agent()
    a._trigger_route("张明", "温度低于18就开空调")
    assert a.check_conditions({"temperature": 22}) == []         # 不满足
    assert a.check_conditions({"temperature": 15})               # 跌破 → 触发
    assert a.devices.states()["ac"]["power"] == "on"
    assert a.check_conditions({"temperature": 15}) == []         # 持续满足，不重复
    a.check_conditions({"temperature": 22})                      # 回升复位
    assert a.check_conditions({"temperature": 15})               # 再次跌破 → 再触发


def test_read_sensors_prefers_source_then_falls_back():
    a = _agent()
    a.sensor_source = None
    a.sensors = {"temperature": 21}
    assert a.read_sensors() == {"temperature": 21}               # 无真实源 → 模拟
    a.sensor_source = type("S", (), {"read": lambda self: {"temperature": 9}})()
    assert a.read_sensors() == {"temperature": 9}                # 有真实源 → 用之
    # 条件触发默认读 read_sensors（这里真实源报 9 < 18 → 触发）
    a._trigger_route("张明", "温度低于18就开空调")
    assert a.check_conditions()


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ triggers: all tests passed")
