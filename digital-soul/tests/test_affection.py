"""真情流露测试。可直接运行：python tests/test_affection.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.affection import is_love_query, love_reply  # noqa: E402


def test_is_love_query():
    assert is_love_query("你想我吗")
    assert is_love_query("你在乎我吗")
    assert not is_love_query("今天几号")


def test_love_reply_by_relation():
    assert "最舍不得" in love_reply("老婆") or "没了魂" in love_reply("老婆")
    assert "心头肉" in love_reply("孙子") or "好好的" in love_reply("孙子")
    assert "养我这么大" in love_reply("妈") or "硬朗" in love_reply("妈")


def test_love_reply_default():
    r = love_reply("发小")
    assert "想" in r or "在乎" in r                      # 没特定关系也真心回


def test_love_reply_present_no_death():
    for rel in ("老伴", "孙子", "妈", ""):
        r = love_reply(rel)
        for bad in ("死", "不在了", "走了", "忌日"):
            assert bad not in r


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ affection: all tests passed")
