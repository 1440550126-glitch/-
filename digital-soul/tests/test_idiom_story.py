"""成语故事测试。可直接运行：python tests/test_idiom_story.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.idiom_story import find, idioms, is_idiom_query, tell  # noqa: E402


def test_idioms_and_find():
    assert "守株待兔" in idioms() and "亡羊补牢" in idioms()
    assert find("讲讲守株待兔") == "守株待兔"
    assert find("今天天气好") is None


def test_is_idiom_query():
    assert is_idiom_query("守株待兔的故事")
    assert is_idiom_query("亡羊补牢什么意思")
    assert not is_idiom_query("守株待兔")            # 没问故事/意思
    assert not is_idiom_query("什么意思")            # 没具体成语


def test_tell():
    t = tell("守株待兔")
    assert "树桩" in t and "下功夫" in t
    assert "为时未晚" in tell("亡羊补牢")
    assert tell("没这成语") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ idiom_story: all tests passed")
