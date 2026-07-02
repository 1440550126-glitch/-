"""专属默契测试。可直接运行：python tests/test_inside_jokes.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.inside_jokes import (  # noqa: E402
    a_callback,
    has_callbacks,
    load,
    match,
    wants_callback,
)

_CFG = {"inside_jokes": [
    {"cue": ["老地方", "老规矩"], "say": "老地方见——还是那家牛肉面，你加辣我不要香菜。",
     "with": "小婷"},
    {"cue": ["天王盖地虎"], "say": "宝塔镇河妖！哈哈，对上了。"},
    {"cue": ["缺回复"]},                            # 缺 say → load 丢弃
    {"say": "缺暗号"},                              # 缺 cue → load 丢弃
]}


def test_load_filters_incomplete():
    items = load(_CFG)
    assert len(items) == 2                          # 两条不全的被丢弃
    assert items[0]["with"] == "小婷"


def test_match_basic():
    assert "牛肉面" in match("还是老地方吧", _CFG, who="小婷")
    assert "宝塔镇河妖" in match("天王盖地虎", _CFG)


def test_match_respects_with():
    # 这条限定跟"小婷"，别人说不触发
    assert match("老地方", _CFG, who="阿强") == ""
    assert match("老地方", _CFG, who="小婷") != ""


def test_match_no_with_anyone():
    # 暗号没限定 with → 谁说都接
    assert match("天王盖地虎", _CFG, who="谁都行") != ""


def test_match_ignores_too_short_cue():
    short = {"inside_jokes": [{"cue": "x", "say": "太短的暗号不算"}]}
    assert match("x", short) == ""                 # 1 字 cue 不匹配


def test_match_empty():
    assert match("随便说点啥", _CFG) == ""
    assert match("老地方", {"inside_jokes": []}) == ""


def test_has_callbacks():
    assert has_callbacks(_CFG)
    assert has_callbacks(_CFG, who="小婷")
    assert not has_callbacks({"inside_jokes": []})


def test_a_callback():
    s = a_callback(_CFG, seed="a")
    assert s and isinstance(s, str)
    # 限定 who → 只在跟该人有关的里挑
    s2 = a_callback(_CFG, who="阿强", seed="a")     # 阿强只能拿到没限定的那条
    assert "宝塔镇河妖" in s2


def test_wants_callback():
    assert wants_callback("说个咱俩的梗")
    assert wants_callback("老规矩是啥来着")
    assert not wants_callback("今天几号")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ inside_jokes: all tests passed")
