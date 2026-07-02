"""亲戚称呼计算器测试。可直接运行：python tests/test_kinship.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.kinship import call_what, parse_steps, term_for  # noqa: E402


def test_parse_steps():
    assert parse_steps("我爸爸的弟弟") == ["f", "YB"]
    assert parse_steps("妈妈的哥哥的儿子") == ["m", "OB", "S"]
    assert parse_steps("爷爷") == []                 # 复合称呼不拆（库里按基本关系）
    assert parse_steps("") == []


def test_common_terms():
    cases = {
        "我爸的哥哥": "伯伯", "我爸的弟弟": "叔叔", "爸爸的姐姐": "姑姑",
        "妈妈的哥哥": "舅舅", "妈妈的妹妹": "姨妈",
        "爸爸的爸爸": "爷爷", "妈妈的爸爸": "外公", "妈妈的妈妈": "外婆",
        "儿子的儿子": "孙子", "女儿的女儿": "外孙女",
        "哥哥的儿子": "侄子", "姐姐的女儿": "外甥女",
    }
    for q, expect in cases.items():
        assert term_for(parse_steps(q)) == expect, q


def test_inlaws_and_cousins():
    assert term_for(parse_steps("妻子的爸爸")) == "岳父"
    assert term_for(parse_steps("丈夫的妈妈")) == "婆婆"
    assert term_for(parse_steps("哥哥的老婆")) == "嫂子"
    assert term_for(parse_steps("妈妈的哥哥的儿子")) == "表哥/表弟"


def test_call_what_messages():
    assert "叔叔" in call_what("我爸的弟弟叫什么")
    assert "没听明白" in call_what("叫什么")          # 没有关系词
    assert "算不准" in call_what("我爸的爸爸的妹妹的孙子")   # 太绕，库里没有


def test_agent_kinship_route_method():
    a = object.__new__(Agent)
    assert "外公" in a.kinship("妈妈的爸爸叫什么")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ kinship: all tests passed")
