"""飞花令测试。可直接运行：python tests/test_feihualing.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.feihualing import (  # noqa: E402
    a_line,
    chars,
    contains,
    extract_char,
    is_feihualing,
    lines_with,
)


def test_chars():
    cs = chars()
    for c in ("月", "花", "春", "风"):
        assert c in cs


def test_lines_with_contains_char():
    for ln in lines_with("月"):
        assert "月" in ln                          # 每句都得带"月"


def test_contains():
    assert contains("床前明月光", "月")
    assert not contains("床前明月光", "花")


def test_a_line_skips_used():
    first = a_line("月", seed="0")
    again = a_line("月", used=[first], seed="0")
    assert again and again != first


def test_a_line_exhausted_empty():
    allm = lines_with("酒")
    assert a_line("酒", used=allm) == ""


def test_extract_char():
    assert extract_char("来句带月的诗") == "月"
    assert extract_char("含花字的诗句") == "花"
    assert extract_char("飞花令，春") == "春"
    assert extract_char("随便聊聊") == ""


def test_is_feihualing():
    assert is_feihualing("玩飞花令")
    assert is_feihualing("来句带月的诗")
    assert is_feihualing("含风字的诗句")
    assert not is_feihualing("今天几号")


def test_config_add():
    cfg = {"feihualing": {"月": ["自家的带月句子月月月"], "雪": ["孤舟蓑笠翁，独钓寒江雪"]}}
    assert "自家的带月句子月月月" in lines_with("月", cfg)
    assert "雪" in chars(cfg)
    assert extract_char("带雪的诗", cfg) == "雪"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ feihualing: all tests passed")
