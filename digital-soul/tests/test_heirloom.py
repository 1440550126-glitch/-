"""遗物 / 信物故事测试。可直接运行：python tests/test_heirloom.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.heirloom import (  # noqa: E402
    bequest_to, collect_heirlooms, find_heirloom, list_items, story_of, where_is,
)


def test_collect_from_config_and_legacy():
    cfg = {"heirlooms": [
        {"item": "怀表", "from": "你爷爷", "year": "1960", "to": "长孙",
         "story": "他戴了三十年", "where": "书房抽屉"},
        "蓝布衫",                                          # 纯字符串也收
    ]}
    legacy = {"heirlooms": [{"item": "钢笔", "to": "小明"}, {"item": "怀表"}]}  # 怀表去重
    out = collect_heirlooms(cfg, legacy)
    names = [it["item"] for it in out]
    assert names == ["怀表", "蓝布衫", "钢笔"]            # 去重保序
    assert out[0]["where"] == "书房抽屉"


def test_find_heirloom_longest_first():
    items = collect_heirlooms({"items": [{"item": "表"}, {"item": "怀表"}]})
    assert find_heirloom(items, "爷爷那块怀表呢")["item"] == "怀表"  # 长名优先
    assert find_heirloom(items, "没提到的东西") is None


def test_story_of():
    it = {"item": "怀表", "from": "你爷爷", "year": "1960",
          "story": "他戴了三十年。", "to": "长孙"}
    s = story_of(it)
    assert "怀表" in s and "你爷爷" in s and "1960" in s
    assert "戴了三十年" in s and "长孙" in s
    assert story_of(None) == ""


def test_bequest_to():
    items = collect_heirlooms({"items": [
        {"item": "怀表", "to": "小明"}, {"item": "钢笔", "to": "小红"}]})
    got = bequest_to(items, "小明")
    assert len(got) == 1 and got[0]["item"] == "怀表"
    assert bequest_to(items, "谁也不是") == []


def test_list_and_where():
    items = collect_heirlooms({"items": [{"item": "怀表", "where": "抽屉"}]})
    assert "怀表" in list_items(items)
    assert where_is(items[0]) == "怀表收在抽屉。"
    assert where_is({"item": "书"}) == ""                 # 没记位置就不说
    assert list_items([]) == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ heirloom: all tests passed")
