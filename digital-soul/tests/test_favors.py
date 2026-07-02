"""人情往来账测试。可直接运行：python tests/test_favors.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.favors import FavorBook, _norm_dir  # noqa: E402


def _book():
    d = tempfile.mkdtemp()
    return FavorBook(pathlib.Path(d) / "favors.json")


def test_norm_dir():
    assert _norm_dir("收到") == "收到"
    assert _norm_dir("人家随来的") == "收到"
    assert _norm_dir("送出") == "送出"
    assert _norm_dir("") == "送出"


def test_balance_and_owe():
    b = _book()
    b.add("老王", 600, direction="收到", event="我家添丁")   # 人家给咱600
    b.add("老王", 500, direction="送出", event="老王儿子结婚")  # 咱给老王500
    assert b.balance_with("老王") == 100                  # 咱还欠老王100
    assert b.we_owe() == [("老王", 100)]
    assert b.they_owe() == []


def test_they_owe():
    b = _book()
    b.add("老李", 800, direction="送出")
    b.add("老李", 300, direction="收到")
    assert b.balance_with("老李") == -500
    assert b.they_owe() == [("老李", 500)]


def test_persistence_and_seed():
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / "favors.json"
    seed = {"records": [{"with": "老张", "amount": 200, "direction": "收到"}]}
    b1 = FavorBook(p, seed=seed)
    assert b1.balance_with("老张") == 200
    b2 = FavorBook(p)                                     # 重新加载，种子不重复灌
    assert len(b2.records) == 1 and b2.balance_with("老张") == 200


def test_describe_and_remind():
    b = _book()
    assert "清爽" in b.describe()
    b.add("老王", 600, direction="收到")
    assert "老王" in b.describe()
    assert "还欠着" in b.remind("老王")
    assert "还没什么往来" in b.remind("陌生人")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ favors: all tests passed")
