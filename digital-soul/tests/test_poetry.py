"""背诗测试。可直接运行：python tests/test_poetry.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.poetry import (  # noqa: E402
    collect, find_title, is_poetry, next_line, recite, titles,
)


def test_next_line():
    assert next_line("床前明月光") == "疑是地上霜"
    assert next_line("锄禾日当午") == "汗滴禾下土"
    assert next_line("最后一句没有下文：低头思故乡") == "" or next_line("低头思故乡") == ""
    assert next_line("不是诗的一句") == ""


def test_collect_merges_config():
    p = collect({"poems": {"自家诗": ["第一句", "第二句"]}})
    assert "自家诗" in p and "静夜思" in p
    assert next_line("第一句", p) == "第二句"


def test_find_and_recite():
    assert find_title("给我背首静夜思") == "静夜思"
    r = recite("春晓")
    assert "春眠不觉晓" in r and "花落知多少" in r
    assert recite("没有的诗") == ""


def test_titles_and_is_poetry():
    assert "悯农" in titles()
    assert is_poetry("床前明月光下一句是啥")
    assert is_poetry("给孙子背首诗")
    assert not is_poetry("今天吃什么")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ poetry: all tests passed")
