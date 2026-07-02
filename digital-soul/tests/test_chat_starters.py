"""没话找话测试。可直接运行：python tests/test_chat_starters.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.chat_starters import is_invite, starter  # noqa: E402


def test_starter_nonempty_and_present():
    s = starter(seed="x", tod="晚上")
    assert s
    for bad in ("死", "忌日", "不在了"):
        assert bad not in s


def test_starter_mentions_people_sometimes():
    # seed 长度可被 3 整除时提到惦记的人
    s = starter(seed="abc", people=["小明"])
    assert "小明" in s


def test_starter_deterministic():
    assert starter(seed="k", tod="清晨") == starter(seed="k", tod="清晨")


def test_is_invite():
    assert is_invite("陪我聊聊天")
    assert is_invite("陪我说说话吧")
    assert not is_invite("帮我关灯")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ chat_starters: all tests passed")
