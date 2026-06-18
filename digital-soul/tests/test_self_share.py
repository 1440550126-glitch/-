"""说说我自己测试。可直接运行：python tests/test_self_share.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.self_share import is_about_me_query, my_day  # noqa: E402


def test_my_day_turns_back():
    s = my_day(tod="傍晚", seed="x")
    assert "你呢" in s                                    # 把话头转回给对方（双向）


def test_my_day_prefers_daily_life():
    s = my_day(daily_life=["在书房写写毛笔字"], tod="上午", seed="aa")  # 偶数用 daily_life
    assert "写写毛笔字" in s and "你呢" in s


def test_my_day_present_tense_no_death():
    for tod in ("清晨", "深夜", "傍晚"):
        s = my_day(tod=tod)
        for bad in ("死", "忌日", "不在了", "走了"):
            assert bad not in s


def test_is_about_me_query():
    assert is_about_me_query("你今天怎么样")
    assert is_about_me_query("你过得好吗")
    assert not is_about_me_query("今天怎么样")            # 没"你"，是问自己
    assert not is_about_me_query("几点了")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ self_share: all tests passed")
