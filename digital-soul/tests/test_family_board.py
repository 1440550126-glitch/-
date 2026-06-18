"""家庭共享·分工板测试。可直接运行：python tests/test_family_board.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.family_board import FamilyBoard  # noqa: E402


def _b():
    return FamilyBoard(pathlib.Path(tempfile.mkdtemp()) / "b.json")


def test_assign_and_describe():
    b = _b()
    b.assign("买菜", who="小明")
    b.assign("接孩子", who="小婷")
    assert b.assign("") is None
    d = b.describe()
    assert "小明—买菜" in d and "小婷—接孩子" in d


def test_for_member():
    b = _b()
    b.assign("买菜", who="小明")
    b.assign("做饭", who="小明")
    b.assign("接孩子", who="小婷")
    mine = [it["what"] for it in b.for_member("小明")]
    assert mine == ["买菜", "做饭"]


def test_done_marks_and_removes_from_pending():
    b = _b()
    b.assign("倒垃圾", who="小明")
    assert b.done("垃圾倒了")["what"] == "倒垃圾"
    assert b.pending() == []
    assert b.done("没有的活") is None


def test_today_and_persist():
    p = pathlib.Path(tempfile.mkdtemp()) / "b.json"
    FamilyBoard(p).assign("买菜", who="小明", when="今天")
    b2 = FamilyBoard(p)
    assert len(b2.today()) == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ family_board: all tests passed")
