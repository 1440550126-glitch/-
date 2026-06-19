"""泡茶测试。可直接运行：python tests/test_tea.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.tea import brew, find_tea, is_tea_query, teas  # noqa: E402


def test_teas_cover():
    ts = teas()
    for t in ("绿茶", "红茶", "普洱", "乌龙"):
        assert t in ts


def test_brew():
    assert "80" in brew("绿茶") or "别用" in brew("绿茶")
    assert "暖胃" in brew("红茶")
    assert "洗茶" in brew("普洱")
    assert brew("可乐") == ""


def test_find_tea_alias_and_longest():
    assert find_tea("龙井怎么泡") == "绿茶"          # 别名
    assert find_tea("铁观音水温多少") == "乌龙"
    assert find_tea("今天天气") == ""


def test_brew_from_sentence():
    assert "绿茶" in brew("绿茶怎么泡好喝")


def test_is_tea_query():
    assert is_tea_query("绿茶怎么泡")
    assert is_tea_query("泡茶有什么讲究")
    assert is_tea_query("铁观音水温多少")
    assert not is_tea_query("今天几号")
    assert not is_tea_query("我爱喝绿茶")            # 没问怎么泡/功效


def test_config_add():
    cfg = {"tea": {"六安瓜片": ["85℃", "泡2分钟", "清香回甘。"]}}
    assert "六安瓜片" in teas(cfg)
    assert "回甘" in brew("六安瓜片", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ tea: all tests passed")
