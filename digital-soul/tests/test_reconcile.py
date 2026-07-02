"""放下 / 和好测试。可直接运行：python tests/test_reconcile.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.reconcile import senses_regret, soothe_regret  # noqa: E402


def test_senses_regret():
    assert senses_regret("我一直没原谅他")
    assert senses_regret("当年要是听你的就好了")
    assert senses_regret("我对不起你们")
    assert not senses_regret("今天挺开心")


def test_soothe_tailored():
    assert "松开" in soothe_regret("我咽不下这口气，没原谅他", name="爸")
    assert "去补" in soothe_regret("我心里愧疚，对不起他")
    assert "往前过" in soothe_regret("我特别后悔当年的决定")
    assert soothe_regret("今天天气好") == ""


def test_soothe_has_name_and_warmth():
    r = soothe_regret("一直放不下这个心结", name="老张")
    assert r.startswith("老张，") and ("解开" in r or "轻" in r)


def test_present_no_death():
    for u in ("我后悔当年", "没原谅他", "对不起他"):
        r = soothe_regret(u)
        for bad in ("死", "不在了", "忌日"):
            assert bad not in r


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ reconcile: all tests passed")
