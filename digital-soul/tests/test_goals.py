"""心愿目标测试。可直接运行：python tests/test_goals.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.goals import GoalBook  # noqa: E402


def test_add_progress_complete_persist():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "g.json"
        b = GoalBook(p)
        assert b.add("  ") is None
        b.add("每周陪爸妈吃饭", now=1)
        assert len(b.open()) == 1
        assert b.note_progress("陪爸妈", "这周做到了")["progress"] == ["这周做到了"]
        assert b.complete("陪爸妈")["status"] == "done"
        assert b.open() == [] and len(b.done()) == 1
        assert len(GoalBook(p).items) == 1                 # 持久化


def test_add_dedupes():
    with tempfile.TemporaryDirectory() as d:
        b = GoalBook(pathlib.Path(d) / "g.json")
        g1 = b.add("学吉他")
        g2 = b.add("学吉他")
        assert g1["text"] == g2["text"] and len(b.items) == 1


def test_summary():
    with tempfile.TemporaryDirectory() as d:
        b = GoalBook(pathlib.Path(d) / "g.json")
        assert "还没立下" in b.summary()
        b.add("跑马拉松")
        b.add("学吉他")
        b.complete("学吉他")
        s = b.summary()
        assert "跑马拉松" in s and "做到的" in s


def test_agent_goal_flow():
    a = object.__new__(Agent)
    with tempfile.TemporaryDirectory() as d:
        a.goals = GoalBook(pathlib.Path(d) / "g.json")
        assert "心愿" in a.set_goal("每天陪妈散步")
        assert "散步" in a.goals_summary()
        assert "做到了" in a.complete_goal("散步")
    a.goals = None
    assert a.set_goal("x") == "" and a.goals_summary() == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ goals: all tests passed")
