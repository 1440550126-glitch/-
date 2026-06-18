"""唠家常测试。可直接运行：python tests/test_smalltalk.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.smalltalk import is_smalltalk, smalltalk_reply  # noqa: E402


def test_is_smalltalk():
    assert is_smalltalk("吃了吗")
    assert is_smalltalk("在吗")
    assert is_smalltalk("最近怎么样")
    assert not is_smalltalk("帮我把灯关了")


def test_replies_match_intent():
    assert "吃" in smalltalk_reply("你吃了吗")
    assert "在" in smalltalk_reply("你在吗")
    assert "忙" in smalltalk_reply("忙啥呢") or "放下" in smalltalk_reply("忙啥呢")
    r = smalltalk_reply("最近怎么样")
    assert "你" in r


def test_reply_deterministic():
    assert smalltalk_reply("吃了吗", seed="x") == smalltalk_reply("吃了吗", seed="x")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ smalltalk: all tests passed")
