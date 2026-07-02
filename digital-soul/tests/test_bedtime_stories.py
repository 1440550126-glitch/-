"""睡前故事测试。可直接运行：python tests/test_bedtime_stories.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.bedtime_stories import (  # noqa: E402
    collect, find, is_request, pick, tell, titles,
)


def test_titles_and_collect():
    assert "龟兔赛跑" in titles()
    merged = collect({"stories": [{"title": "新故事", "text": "很久很久以前……"}]})
    assert any(s["title"] == "新故事" for s in merged)
    # 重复标题不叠加
    assert len(collect({"stories": [{"title": "龟兔赛跑", "text": "x"}]})) == len(titles())


def test_pick_rotates():
    s1 = pick()
    s2 = pick(exclude=[s1["title"]])
    assert s1["title"] != s2["title"]


def test_find():
    assert find(None, "给我讲龟兔赛跑")["title"] == "龟兔赛跑"
    assert find(None, "没有这个故事") is None


def test_tell():
    t = tell({"title": "小马过河", "text": "小马要过河。"})
    assert "小马过河" in t and "闭上眼睛" in t and "甜甜的梦" in t
    assert tell(None) == ""


def test_is_request():
    assert is_request("给娃讲个睡前故事")
    assert is_request("哄睡")
    assert not is_request("讲讲你的过去")            # 那是家史，不是睡前故事


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ bedtime_stories: all tests passed")
