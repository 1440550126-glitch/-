"""自主规划测试。可直接运行：python tests/test_plan.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.memory import Memory  # noqa: E402
from dsoul.planner import Planner, PlanBook  # noqa: E402


def _pb():
    return PlanBook(tempfile.mktemp(suffix=".json"))


def test_planbook_set_open_done():
    p = _pb()
    p.set([{"kind": "remind", "text": "歇会儿"}, {"kind": "checkin", "text": "问候家人"}])
    assert len(p.open()) == 2 and p.fresh_today()
    assert p.mark_done(p.open()[0]["id"]) is True
    assert len(p.done()) == 1 and len(p.open()) == 1


def test_planbook_persists():
    path = tempfile.mktemp(suffix=".json")
    PlanBook(path).set([{"kind": "remind", "text": "x"}])
    assert len(PlanBook(path).open()) == 1


def test_heuristic_plan_from_tasks_and_reflections():
    pl = Planner()
    open_tasks = [{"agent": "爱马仕", "instruction": "整理相册", "attempts": 1}]
    refl = ["最近「加班」被反复提起，得放心上"]
    items = pl.make_plan(refl, open_tasks, mood="哀")
    kinds = [i["kind"] for i in items]
    assert "followup" in kinds                              # 欠账 → 跟进
    assert "remind" in kinds                                # 情绪低落 / 加班 → 提醒
    assert any("整理相册" in i["text"] for i in items)


def test_tick_plans_then_advances():
    m = Memory(tempfile.mktemp(suffix=".json"))
    m.add("最近大家多次流露喜悦", source="reflection", tags=["reflection"])
    a = object.__new__(Agent)                               # 只测心跳逻辑，不走完整构造
    a.memory = m
    a.reflector = None
    a.journal = None
    a.tasks = None
    a.hub = None
    a.emotions = None
    a.planner = Planner()
    a.plan = _pb()
    out = a.tick()
    assert out["plan"]                                      # 排了今天的计划
    assert a.plan.done()                                    # 推进：提醒类一次即完成
    out2 = a.tick()                                         # 同一天不重复排
    assert out2["plan"] == []


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ plan: all tests passed")
