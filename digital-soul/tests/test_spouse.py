"""老伴专属（夫妻之间）测试。可直接运行：python tests/test_spouse.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.spouse import (  # noqa: E402
    anniversary_words, call_name, care_words, comfort_lonely, goodnight,
    is_anniversary, is_spouse, love_story, pick_endearment, senses_longing,
    senses_upset, soothe, spouse_profile, years_married,
)

CFG = {
    "name": "秀兰", "call": "老婆子", "self_call": "老头子",
    "met": "1972年在纺织厂，她在我隔壁车间。",
    "married": "1975-10-01",
    "story": ["1972 纺织厂相识", "1975 结婚，借辆自行车当婚车"],
    "promises": ["说好要一起去看天安门，还没去成。"],
    "care": ["记得按时吃降压药。", "天冷加衣，别舍不得。", "一个人也好好吃饭。"],
    "endearments": ["这辈子娶到你，是我最大的福气。", "我不在了，你也要笑着过。"],
}


def test_profile_from_config():
    p = spouse_profile(CFG)
    assert p["name"] == "秀兰" and p["call"] == "老婆子"
    assert p["married"] == "1975-10-01"


def test_profile_inferred_from_family():
    fam = {"members": [{"name": "翠花", "relation": "老伴"}, {"name": "小明", "relation": "孙子"}]}
    p = spouse_profile(None, family=fam)
    assert p["name"] == "翠花" and p["relation"] == "老伴"
    assert p["call"] == "翠花"                              # 没配昵称就用名字


def test_no_spouse_returns_empty():
    assert spouse_profile(None, family={"members": [{"name": "小明", "relation": "孙子"}]}) == {}
    assert spouse_profile(None) == {}


def test_is_spouse():
    p = spouse_profile(CFG)
    assert is_spouse(p, "秀兰")
    assert is_spouse(p, "张三", relation="老婆")
    assert not is_spouse(p, "邻居老李")
    assert not is_spouse({}, "秀兰")


def test_love_story():
    s = love_story(spouse_profile(CFG))
    assert "纺织厂" in s and "1975-10-01" in s and "值了" in s
    assert love_story({}) == ""


def test_years_and_anniversary():
    p = spouse_profile(CFG)
    assert years_married(p, datetime(2025, 1, 1)) == 50
    assert is_anniversary(p, datetime(2026, 10, 1))
    assert not is_anniversary(p, datetime(2026, 10, 2))
    w = anniversary_words(p, datetime(2026, 10, 1))
    assert "结婚纪念日" in w and "老婆子" in w
    assert anniversary_words(p, datetime(2026, 6, 1)) == ""   # 非纪念日当天为空


def test_care_words_rotate():
    p = spouse_profile(CFG)
    a = care_words(p, datetime(2026, 1, 1), limit=2)
    b = care_words(p, datetime(2026, 1, 2), limit=2)
    assert len(a) == 2 and a != b                          # 每天轮换，不重样
    assert all(isinstance(x, str) for x in a)
    assert care_words({}, datetime.now()) == []


def test_longing_and_comfort():
    p = spouse_profile(CFG)
    assert senses_longing("老头子，我好想你")
    assert senses_longing("夜里睡不着")
    assert not senses_longing("今天天气真好")
    c = comfort_lonely(p, "我好想你")
    assert "老婆子" in c and "一直都在" in c
    assert "守着你睡" in comfort_lonely(p, "我睡不着")
    assert comfort_lonely({}, "想你") == ""


def test_call_and_endearment():
    p = spouse_profile(CFG)
    assert call_name(p) == "老婆子"
    assert call_name({}) == "老伴"
    assert pick_endearment(p) in CFG["endearments"]
    assert pick_endearment({}) == ""


def test_upset_and_soothe():
    p = spouse_profile(CFG)
    assert senses_upset("今天真把我气死了")
    assert senses_upset("好委屈")
    assert not senses_upset("今天挺顺心")
    s = soothe(p, "我好烦")
    assert "老婆子" in s and "别气了" in s
    assert soothe({}, "烦") == ""


def test_goodnight():
    p = spouse_profile(CFG)
    g = goodnight(p)
    assert "老婆子" in g and "做个好梦" in g
    assert goodnight({}) == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ spouse: all tests passed")
