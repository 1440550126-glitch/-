"""待办清单测试。可直接运行：python tests/test_todo.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.todo import TodoList  # noqa: E402


def _t():
    return TodoList(pathlib.Path(tempfile.mkdtemp()) / "t.json")


def test_add_and_pending():
    t = _t()
    t.add("交电费")
    t.add("还书")
    assert t.add("") is None
    assert t.pending() == ["交电费", "还书"]


def test_add_dedupes_open():
    t = _t()
    t.add("交电费")
    t.add("交电费")
    assert t.pending() == ["交电费"]


def test_done_fuzzy():
    t = _t()
    t.add("给老李回电话")
    assert t.done("老李回电话")["task"] == "给老李回电话"
    assert t.pending() == []
    assert t.done("没有的事") is None


def test_describe_and_clear():
    t = _t()
    assert "清爽" in t.describe()
    t.add("交电费")
    assert "交电费" in t.describe()
    t.done("交电费")
    assert t.clear_done() == 1


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "t.json"
    TodoList(p).add("还书")
    assert TodoList(p).pending() == ["还书"]


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ todo: all tests passed")
