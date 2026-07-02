"""速记便签测试。可直接运行：python tests/test_notes.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.notes import NoteBook  # noqa: E402


def test_add_recent_search_clear_persist():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "n.json"
        b = NoteBook(p)
        assert b.add("  ") is None                  # 空白不收
        b.add("明天买菜", now=1)
        b.add("给妈打电话", now=2)
        assert b.recent() == ["给妈打电话", "明天买菜"]   # 最近在前
        assert b.search("买菜") == ["明天买菜"]
        assert b.search("") == []
        assert NoteBook(p).recent() == ["给妈打电话", "明天买菜"]  # 持久化
        assert b.clear() == 2 and b.recent() == []


def test_agent_jot_and_recent_and_safe():
    a = object.__new__(Agent)
    with tempfile.TemporaryDirectory() as d:
        a.notes = NoteBook(pathlib.Path(d) / "n.json")
        assert "买菜" in a.jot_note("明天买菜")
        assert a.recent_notes() == ["明天买菜"]
    a.notes = None
    assert a.jot_note("x") == "" and a.recent_notes() == []


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ notes: all tests passed")
