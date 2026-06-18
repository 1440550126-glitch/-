"""像人一样接话测试。可直接运行：python tests/test_followup.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.followup import (  # noqa: E402
    followup, generic_followup, is_sharing,
)


def test_followup_tailored():
    assert "玩得" in followup("我今天去了趟公园")
    assert "他最近" in followup("路上碰到老王了")
    assert "难不难" in followup("我最近在学书法")
    assert "味道" in followup("我中午炖了排骨")
    assert "养着" in followup("这两天有点感冒")


def test_followup_skips_questions():
    assert followup("你去过北京吗") == ""               # 是提问，不追问
    assert followup("今天几号") == ""


def test_is_sharing():
    assert is_sharing("我今天去了趟外婆家")
    assert not is_sharing("去吗")                        # 太短 + 提问
    assert not is_sharing("你买了吗")                    # 提问


def test_generic_followup():
    assert generic_followup() and "呢" in generic_followup("x") or "讲" in generic_followup("x")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ followup: all tests passed")
