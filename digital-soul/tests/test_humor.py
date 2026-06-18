"""幽默测试。可直接运行：python tests/test_humor.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.humor import (  # noqa: E402
    banter, collect_jokes, is_joke_request, is_teasing, tell_joke,
)


def test_collect_jokes_merges():
    js = collect_jokes({"jokes": ["自定义段子一则", "我这记性好得很——除了想不起来的，全记得。"]})
    assert "自定义段子一则" in js
    assert js.count("我这记性好得很——除了想不起来的，全记得。") == 1   # 去重


def test_is_joke_request():
    assert is_joke_request("给我讲个笑话")
    assert is_joke_request("逗我笑一个")
    assert not is_joke_request("今天好累")


def test_is_teasing():
    assert is_teasing("你真笨")
    assert not is_teasing("你真好")


def test_tell_joke_rotates():
    js = collect_jokes()
    first = tell_joke(js)
    second = tell_joke(js, exclude=[first])
    assert first and second and first != second
    # 全讲过了也不报错（从头来）
    assert tell_joke(js, exclude=js) in js


def test_banter():
    assert banter(seed="a")
    assert banter(seed="abc") in (
        "哟，今天嘴这么甜，是有事求我吧？", "就你机灵，行行行，说不过你。",
        "哈哈，贫嘴，跟谁学的这张嘴？", "得嘞，你赢，我认输还不行嘛。")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ humor: all tests passed")
