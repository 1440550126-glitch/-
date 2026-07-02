"""麻将术语/规则测试。可直接运行：python tests/test_mahjong.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.mahjong import (  # noqa: E402
    basics, count, explain_term, find_pattern, find_term, is_mahjong_query,
    patterns, terms, tiles_intro,
)


def test_terms_present():
    t = terms()
    for k in ("碰", "杠", "吃", "听", "胡", "自摸", "点炮"):
        assert k in t
    assert count() >= 20


def test_explain_term_and_alias():
    assert "三张" in explain_term("碰")
    assert explain_term("放炮") == explain_term("点炮")    # 别名归一
    assert explain_term("对子") == explain_term("将")
    assert explain_term("不存在") == ""


def test_find_term_longest_and_alias():
    assert find_term("自摸是什么意思") == "自摸"           # 别被"摸"之类短词截胡
    assert find_term("对对胡咋胡的") == "碰碰胡"           # 别名→正名
    assert find_term("今天天气好") == ""


def test_patterns_and_find():
    names = [n for n, _ in patterns()]
    assert "碰碰胡" in names and "清一色" in names and "七对" in names
    assert find_pattern("清一色怎么算").startswith("清一色：")
    assert find_pattern("对对胡是啥").startswith("碰碰胡：")   # 别名也能找到
    assert find_pattern("我想喝水") == ""


def test_tiles_and_basics():
    ti = tiles_intro()
    assert "万" in ti and "筒" in ti and "条" in ti and "一百三十六" in ti
    b = basics()
    assert "四副" in b and "将" in b and ("自摸" in b)
    assert "别上头" in b                                  # 留了句小赌怡情的提醒


def test_is_mahjong_query_gating():
    assert is_mahjong_query("麻将怎么玩")
    assert is_mahjong_query("碰是什么意思")
    assert is_mahjong_query("清一色怎么胡")
    assert not is_mahjong_query("我想吃个苹果")            # "吃"是术语但无问询意图
    assert not is_mahjong_query("今天打球去")
    assert not is_mahjong_query("麻将馆在哪")              # 没问规则/玩法


def test_config_extra_terms_and_patterns():
    cfg = {"mahjong": {"terms": {"血战到底": "三家胡完才结束的打法"},
                       "patterns": [["天胡", "庄家起手就胡，传说级"]]}}
    assert explain_term("血战到底", cfg).startswith("三家")
    assert "天胡" in [n for n, _ in patterns(cfg)]
    assert find_pattern("天胡是啥", cfg).startswith("天胡：")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ mahjong: all tests passed")
