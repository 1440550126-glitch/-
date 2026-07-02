"""喜好测试。可直接运行：python tests/test_preferences.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.preferences import (  # noqa: E402
    answer_preference, collect_preferences, dislikes_of, has_any, likes_of,
    opinion_on,
)

CFG = {
    "likes": {"食物": ["红烧肉", "饺子"], "季节": "秋天", "消遣": ["下象棋", "听评书"]},
    "dislikes": {"食物": ["香菜"]},
}


def test_collect_merges_identity():
    idy = {"preferences": {"likes": {"食物": ["饺子", "面条"], "球队": ["国安"]}}}
    p = collect_preferences(CFG, idy)
    assert p["likes"]["食物"] == ["红烧肉", "饺子", "面条"]   # 合并去重
    assert p["likes"]["球队"] == ["国安"]
    assert p["likes"]["季节"] == ["秋天"]                   # 标量转列表
    assert has_any(p) and not has_any({})


def test_answer_like_food():
    p = collect_preferences(CFG)
    a = answer_preference(p, "你爱吃什么")
    assert "红烧肉" in a and "百吃不厌" in a
    assert likes_of(p, "消遣") == ["下象棋", "听评书"]


def test_answer_like_category():
    p = collect_preferences(CFG)
    a = answer_preference(p, "你喜欢什么季节")
    assert "秋天" in a and "偏爱" in a                      # 非吃喝类用"偏爱"


def test_answer_dislike():
    p = collect_preferences(CFG)
    a = answer_preference(p, "你讨厌吃什么")
    assert "香菜" in a and "不想碰" in a
    assert dislikes_of(p, "食物") == ["香菜"]


def test_answer_non_question_empty():
    assert answer_preference(collect_preferences(CFG), "今天天气好") == ""


def test_opinion_on():
    p = collect_preferences(CFG)
    assert "红烧肉" in opinion_on(p, "晚上吃红烧肉好不好")
    assert "香菜" in opinion_on(p, "这菜放了香菜")
    assert opinion_on(p, "聊点别的") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ preferences: all tests passed")
