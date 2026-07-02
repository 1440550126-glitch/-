"""甜言蜜语测试。可直接运行：python tests/test_sweet_talk.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.sweet_talk import (  # noqa: E402
    detect_kind,
    is_sweet_request,
    sweet_line,
)


def test_sweet_line_kinds():
    assert sweet_line("情话", seed="0")
    c = sweet_line("土味", seed="0")
    assert "星星" in c or "胃口" in c or "属于你" in c or "视力" in c or "太阳" in c or "数学" in c or "空位" in c or "心里" in c
    assert sweet_line("夸赞", seed="0")


def test_sweet_line_reproducible():
    assert sweet_line("情话", seed="x") == sweet_line("情话", seed="x")


def test_detect_kind():
    assert detect_kind("说句土味情话") == "土味"
    assert detect_kind("夸夸我") == "夸赞"
    assert detect_kind("说句情话") == "情话"


def test_is_sweet_request():
    assert is_sweet_request("说句情话")
    assert is_sweet_request("来个土味情话")
    assert is_sweet_request("夸夸我")
    assert is_sweet_request("撩我一下")
    assert not is_sweet_request("今天几号")


def test_config_adds():
    cfg = {"sweet_talk": {"love": ["自家的情话：非你不可"], "土味": ["自家土味"]}}
    assert "非你不可" in sweet_line("情话", seed="", config=cfg)
    assert "自家土味" in sweet_line("土味", seed="", config=cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ sweet_talk: all tests passed")
