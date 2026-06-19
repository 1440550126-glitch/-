"""急救常识测试。可直接运行：python tests/test_first_aid.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.first_aid import advice, detect, is_firstaid_query  # noqa: E402


def test_detect():
    assert detect("手被开水烫了") == "烫伤"
    assert detect("孩子流鼻血了") == "流鼻血"
    assert detect("吃饭噎着了") == "噎着"
    assert detect("今天天气好") is None


def test_is_firstaid_query():
    assert is_firstaid_query("烫伤了怎么办")
    assert is_firstaid_query("崴脚了咋办")
    assert not is_firstaid_query("烫伤了")            # 没问怎么办
    assert not is_firstaid_query("今天怎么办")        # 没具体伤情


def test_advice():
    assert "凉水冲" in advice("被烫了怎么办")
    assert "别仰头" in advice("流鼻血怎么办")
    assert "海姆立克" in advice("噎着了咋办")
    assert "破伤风" in advice("手割破了怎么办")
    assert advice("聊聊天") == ""


def test_advice_directs_to_help():
    # 严重时都提示就医/120
    assert "120" in advice("噎着了") or "医院" in advice("烫伤了")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ first_aid: all tests passed")
