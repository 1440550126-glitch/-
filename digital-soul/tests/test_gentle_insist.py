"""该犟就犟 / 托住测试。可直接运行：python tests/test_gentle_insist.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.gentle_insist import (  # noqa: E402
    hold, insist, senses_despair, senses_self_neglect,
)


def test_senses_self_neglect():
    assert senses_self_neglect("我不吃药了")
    assert senses_self_neglect("我不去医院")
    assert senses_self_neglect("今天不睡了")
    assert not senses_self_neglect("我吃过药了")


def test_insist_pushes_back():
    assert "药得按时吃" in insist("我不吃药了", name="妈")
    assert "身体要紧" in insist("我不想看病")
    assert "悠着点" in insist("最近太拼了")
    assert insist("今天天气好") == ""


def test_senses_despair():
    assert senses_despair("我不想活了")
    assert senses_despair("活着没意思")
    assert not senses_despair("今天有点累")


def test_hold_is_warm_and_connects():
    h = hold(name="老张", call_who="闺女")
    assert h.startswith("老张，")
    assert "要紧" in h and "一起扛" in h
    assert "闺女" in h and "一直在你身边" in h
    # 没指定可打电话的人时，引向找人/找医生
    h2 = hold()
    assert "说说话" in h2 or "医生" in h2


def test_hold_no_dismissal():
    h = hold(name="妈")
    for bad in ("别矫情", "想开点", "至于吗", "矫情"):
        assert bad not in h                              # 不轻慢、不说教


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ gentle_insist: all tests passed")
