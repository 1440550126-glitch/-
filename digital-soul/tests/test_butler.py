"""贾维斯式管家层测试。可直接运行：python tests/test_butler.py"""

import pathlib
import sys
import tempfile
import types
from datetime import date, datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.butler import daily_brief, diagnostics, diagnostics_text  # noqa: E402


class _Plan:
    def open(self):
        return [{"text": "提醒主人按时喝水"}]


class _Tasks:
    def open(self):
        return [{"instruction": "整理相册", "agent": "爱马仕"}]


def _agent(known=True, obey=True):
    a = object.__new__(Agent)
    a.identity = {"name": "张明", "assistant": {"address": "先生"}}
    a.llm = types.SimpleNamespace(available=True)
    a.memory = types.SimpleNamespace(items=[1, 2, 3])
    a.perception = None
    a.hub = types.SimpleNamespace(names=lambda: ["爱马仕", "openclaw"])
    a.tasks = _Tasks()
    a.plan = _Plan()
    a.emotions = None
    a.recent_reflections = lambda k=5: ["最近加班的事提得多"]
    return a


def test_daily_brief_assembles_sections():
    a = _agent()
    txt = daily_brief(a, present=["张明"], addr="先生")
    assert "先生" in txt
    assert "提醒主人按时喝水" in txt        # 今天的计划
    assert "整理相册" in txt                # 欠账
    assert "加班" in txt                    # 领悟


def test_diagnostics_reports_subsystems():
    a = _agent()
    d = diagnostics(a)
    assert d["llm"] is True and d["memory"] == 3 and d["agents"] == ["爱马仕", "openclaw"]
    txt = diagnostics_text(a, "先生")
    assert "先生" in txt and "记忆 3 条" in txt and "大模型在线" in txt


def test_route_brief_and_diag_and_wake():
    a = _agent()
    owner = {"known": True, "name": "张明", "obey": True}
    assert "提醒主人按时喝水" in a._butler_route("给我来份简报", owner)
    assert "大模型在线" in a._butler_route("做个系统自检", owner)
    assert "吩咐" in a._butler_route("贾维斯", owner)            # 点名待命
    assert a._butler_route("今天天气不错", owner) is None        # 普通闲聊不拦截


def test_butler_refuses_strangers():
    a = _agent()
    stranger = {"known": False, "name": "路人", "obey": False}
    assert a._butler_route("简报", stranger) is None             # 不对外人汇报（隐私）


def test_brief_includes_core_people():
    from dsoul.authority import Authority
    from dsoul.memory import Memory
    a = object.__new__(Agent)
    a.identity = {"name": "张明"}
    a.emotions = None
    a.plan = None
    a.tasks = None
    a.recent_reflections = lambda k=1: []
    a._graph_cache = None
    m = Memory(tempfile.mktemp(suffix=".json"))
    for t in ["小婷和张明去打球", "小婷陪张明散步"]:
        m.add(t, source="x")
    a.memory = m
    a.authority = Authority({"people": [
        {"name": "张明", "relation": "本人", "trust": "owner"},
        {"name": "小婷", "relation": "老婆", "trust": "family"}]})
    txt = daily_brief(a, present=["张明"], addr="先生")
    assert "小婷" in txt                                   # 核心人物进了简报


def test_morning_brief_window():
    a = object.__new__(Agent)
    a._briefed_on = None
    assert a._should_morning_brief(datetime(2026, 1, 1, 8, 0)) is True    # 清晨
    assert a._should_morning_brief(datetime(2026, 1, 1, 15, 0)) is False  # 下午不主动
    a._briefed_on = date.today().isoformat()
    assert a._should_morning_brief(datetime(2026, 1, 1, 8, 0)) is False   # 今天已报过


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ butler: all tests passed")
