"""派活待办本测试。可直接运行：python tests/test_tasks.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.tasks import TaskBook  # noqa: E402


def _tb():
    return TaskBook(tempfile.mktemp(suffix=".json"))


def test_failure_becomes_open_todo():
    tb = _tb()
    tb.record("爱马仕", "整理相册", ok=False, detail="超时")
    assert len(tb.open()) == 1 and tb.done() == []


def test_repeated_failure_accumulates_attempts():
    tb = _tb()
    tb.record("爱马仕", "整理相册", ok=False)
    tb.record("爱马仕", "整理相册", ok=False)  # 同一件事再失败 → 累加，不新增
    op = tb.open()
    assert len(op) == 1 and op[0]["attempts"] == 2


def test_success_closes_the_todo():
    tb = _tb()
    tb.record("openclaw", "打包", ok=False)
    tb.record("openclaw", "打包", ok=True, detail="done")  # 后来成功 → 关闭
    assert tb.open() == []
    assert len(tb.done()) == 1 and tb.done()[0]["attempts"] == 2


def test_mark_done():
    tb = _tb()
    tid = tb.record("a", "x", ok=False)
    assert tb.mark_done(tid) is True
    assert tb.open() == []


def test_persists_across_reload():
    p = tempfile.mktemp(suffix=".json")
    TaskBook(p).record("a", "x", ok=False)
    assert len(TaskBook(p).open()) == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ tasks: all tests passed")
