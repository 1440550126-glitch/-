"""起名取名测试。可直接运行：python tests/test_naming.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.naming import (  # noqa: E402
    categories, chars_for, explain_char, explain_request, find_wish,
    is_naming_query, suggest_names, tips,
)


def test_categories_nonempty():
    cats = categories()
    assert "品德" in cats and "才智" in cats and "平安" in cats
    assert len(cats) >= 6


def test_find_wish_from_speech():
    assert find_wish("想给孩子起个聪明点的名字") == "才智"
    assert find_wish("要个平平安安的") == "平安"
    assert find_wish("起个有出息的名字") == "志向"
    assert find_wish("名字好听优雅些") == "美好"
    assert find_wish("随便") is None              # 听不出愿望


def test_chars_for_and_explain():
    pairs = chars_for("才智")
    assert pairs and all(len(p) == 2 for p in pairs)
    chs = [c for c, _ in pairs]
    assert "睿" in chs or "慧" in chs
    assert explain_char("睿")                      # 有寓意
    assert explain_char("囧") == ""                # 不在表里


def test_suggest_names_with_surname():
    names = suggest_names(surname="李", wish="才智", n=3, seed="bb")
    assert len(names) == 3
    for full, mean in names:
        assert full.startswith("李") and len(full) == 3   # 姓 + 两字名
        assert mean                                       # 都有解释
    # 候选不重复
    assert len({f for f, _ in names}) == 3


def test_suggest_names_respects_generation_char():
    cfg = {"naming": {"generation": "德"}}
    names = suggest_names(surname="王", wish="平安", n=2, seed="x", config=cfg)
    assert len(names) == 2
    for full, mean in names:
        assert full[:2] == "王德"                  # 姓 + 字辈在前
        assert "字辈" in mean


def test_config_extra_chars():
    cfg = {"naming": {"chars": {"家传": [["祖", "不忘根本"], {"char": "宗", "mean": "光宗耀祖"}]}}}
    assert "家传" in categories(cfg)
    chs = [c for c, _ in chars_for("家传", cfg)]
    assert "祖" in chs and "宗" in chs
    assert explain_char("宗", cfg) == "光宗耀祖"


def test_is_naming_query_gating():
    assert is_naming_query("帮我给孩子起个名字")
    assert is_naming_query("取个有寓意的大名")
    assert not is_naming_query("名字这东西无所谓")    # 有"名字"但无起名意图
    assert not is_naming_query("今天天气不错")


def test_explain_request_detects_char():
    assert explain_request("睿字起名什么寓意") == "睿"
    assert explain_request("康字好不好") == "康"
    assert explain_request("今天吃什么") == ""


def test_tips_present():
    t = tips()
    assert t and any("谐音" in x for x in t)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ naming: all tests passed")
