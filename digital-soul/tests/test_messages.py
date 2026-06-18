"""捎话测试。可直接运行：python tests/test_messages.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.messages import Messages  # noqa: E402


def _m():
    return Messages(pathlib.Path(tempfile.mkdtemp()) / "m.json")


def test_leave_and_pending():
    m = _m()
    m.leave("小明", "妈喊你吃饭", frm="妈")
    assert m.leave("", "空收件人") is None
    pend = m.pending_for("小明")
    assert len(pend) == 1 and pend[0]["text"] == "妈喊你吃饭"


def test_deliver_marks_done():
    m = _m()
    m.leave("小明", "记得带伞", frm="爸")
    out = m.deliver("小明")
    assert out and "爸" in out[0] and "记得带伞" in out[0]
    assert m.pending_for("小明") == []                   # 捎到后就不再 pending
    assert m.deliver("小明") == []


def test_fuzzy_name_match():
    m = _m()
    m.leave("小明", "回个电话")
    assert m.pending_for("我们家小明")                    # 子串也能对上


def test_describe_and_persist():
    p = pathlib.Path(tempfile.mkdtemp()) / "m.json"
    Messages(p).leave("小红", "早点回家", frm="奶奶")
    m2 = Messages(p)
    assert "小红" in m2.describe()
    assert m2.deliver("小红")[0].startswith("奶奶")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ messages: all tests passed")
