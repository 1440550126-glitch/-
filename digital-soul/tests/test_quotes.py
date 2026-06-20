"""名言金句测试。可直接运行：python tests/test_quotes.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.quotes import (  # noqa: E402
    a_quote, count, find_theme, is_quote_query, quotes_for, several, themes,
)


def test_themes_and_count():
    ts = themes()
    for k in ("读书治学", "坚持", "立志", "诚信品德", "惜时", "逆境"):
        assert k in ts
    assert count() >= 30


def test_find_theme_alias():
    assert find_theme("关于坚持的名言") == "坚持"
    assert find_theme("来句励志的") == "立志"
    assert find_theme("珍惜时间的话") == "惜时"
    assert find_theme("遇到挫折该咋办") == "逆境"
    assert find_theme("今天天气好") is None


def test_quotes_have_attribution():
    for theme in themes():
        for text, by in quotes_for(theme):
            assert text and by                       # 每句都有内容和出处
    # 抽查一句经典在不在
    allq = [t for theme in themes() for t, _ in quotes_for(theme)]
    assert any("锲而不舍" in t for t in allq)


def test_a_quote_formats_with_source():
    s = a_quote("坚持", seed="x")
    assert s.startswith("「") and "——" in s          # 「句」——出处
    # 没主题也能来一句
    assert a_quote(seed="any")


def test_a_quote_deterministic():
    assert a_quote("立志", seed="same") == a_quote("立志", seed="same")


def test_several_joins_multiple():
    s = several("读书", n=2, seed="y")
    assert s.count("——") >= 2 and s.endswith("。")
    assert several("不存在的主题") == ""


def test_is_quote_query_gating():
    assert is_quote_query("来句名言")
    assert is_quote_query("给我个座右铭")
    assert is_quote_query("关于诚信的金句")
    assert is_quote_query("关于时间的句子")            # 句子 + 主题
    assert not is_quote_query("今天天气好")
    assert not is_quote_query("外公常说啥")            # 那是个人语录，不归这
    assert not is_quote_query("我一直在坚持锻炼")       # 提到主题词但不是求名言 → 别误判（留给夸夸）
    assert not is_quote_query("明天面试好紧张")        # 打气场合 → 留给 encourage


def test_config_extra_quotes():
    cfg = {"quotes": {"读书治学": [["种一棵树最好的时间是十年前", "谚语"]],
                      "拼搏": [{"text": "不要温和地走进那个良夜", "by": "狄兰·托马斯"}]}}
    assert "拼搏" in themes(cfg)
    allq = [t for t, _ in quotes_for("读书治学", cfg)]
    assert any("种一棵树" in t for t in allq)
    assert quotes_for("拼搏", cfg)[0][1] == "狄兰·托马斯"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ quotes: all tests passed")
