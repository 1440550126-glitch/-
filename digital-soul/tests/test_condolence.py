"""告别与释怀测试。可直接运行：python tests/test_condolence.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.condolence import console, senses_mourning  # noqa: E402


def test_senses_mourning():
    assert senses_mourning("我好想念你")
    assert senses_mourning("你走得太突然了")
    assert senses_mourning("还没来得及好好告别")
    assert not senses_mourning("今天吃什么")


def test_console_regret():
    r = console("我好后悔没能见你最后一面", name="小婷")
    assert r.startswith("小婷，") and "遗憾" in r
    assert "记挂" in r and "好好" in r


def test_console_sudden():
    assert "不怪你" in console("你怎么就突然走了")


def test_console_general():
    assert "一直在你心里" in console("我好想念你")


def test_console_present_and_warm():
    r = console("好想你了")
    assert "别哭" in r or "记挂" in r
    # 不渲染恐惧/不祥
    for bad in ("可怕", "不祥", "凶"):
        assert bad not in r


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ condolence: all tests passed")
