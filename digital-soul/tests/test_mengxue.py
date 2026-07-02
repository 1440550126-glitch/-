"""蒙学测试。可直接运行：python tests/test_mengxue.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.mengxue import (  # noqa: E402
    classics,
    find_classic,
    pair_rhyme,
    recite,
    times_query_row,
    times_row,
    times_table,
    wants_classic,
    wants_times_table,
)


def test_classics_list():
    cs = classics()
    for c in ("三字经", "弟子规", "百家姓", "千字文"):
        assert c in cs


def test_find_classic():
    assert find_classic("给我背背三字经") == "三字经"
    assert find_classic("弟子规怎么念") == "弟子规"
    assert find_classic("随便聊聊") == ""


def test_recite_opening():
    s = recite("三字经")
    assert "人之初，性本善" in s and "三字经" in s
    assert recite("查无此书") == ""


def test_pair_rhyme_forms():
    assert pair_rhyme(7, 3) == "三七二十一"      # 大于10不加"得"
    assert pair_rhyme(2, 3) == "二三得六"        # 小于10加"得"
    assert pair_rhyme(1, 1) == "一一得一"
    assert pair_rhyme(2, 5) == "二五一十"        # 10→一十
    assert pair_rhyme(9, 9) == "九九八十一"
    assert pair_rhyme(7, 7) == "七七四十九"


def test_pair_rhyme_order_independent():
    assert pair_rhyme(3, 7) == pair_rhyme(7, 3)


def test_times_row():
    r = times_row(7)
    assert r.startswith("一七得七")
    assert "七七四十九" in r
    assert r.endswith("。")


def test_times_table_has_nine_rows():
    t = times_table()
    assert t.count("\n") == 8                      # 9 行 → 8 个换行
    assert "九九八十一" in t


def test_wants_classic():
    assert wants_classic("背一段弟子规")
    assert wants_classic("三字经")                 # 光报名字也算
    assert not wants_classic("今天几号")


def test_wants_times_table():
    assert wants_times_table("背乘法口诀")
    assert wants_times_table("九九表给我念念")
    assert wants_times_table("三的乘法口诀")
    assert not wants_times_table("六乘七等于几")    # 这是算术，归日常问答


def test_times_query_row():
    assert times_query_row("七的乘法口诀") == 7
    assert times_query_row("背3的口诀") == 3


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ mengxue: all tests passed")
