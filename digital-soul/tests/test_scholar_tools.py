"""文房四宝测试。可直接运行：python tests/test_scholar_tools.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.scholar_tools import (  # noqa: E402
    count, explain, find_treasure, is_scholar_query, overview, treasures,
)


def test_treasures_present():
    ts = treasures()
    for k in ("笔", "墨", "纸", "砚"):
        assert k in ts
    assert count() >= 4


def test_find_treasure_alias():
    assert find_treasure("宣纸怎么用")[0] == "纸"
    assert find_treasure("徽墨好不好")[0] == "墨"
    assert find_treasure("端砚贵吗")[0] == "砚"
    assert find_treasure("今天天气好") is None


def test_explain_has_famous_origin():
    assert "湖" in explain("笔") or "狼毫" in explain("笔")
    assert "徽墨" in explain("墨")
    assert "宣纸" in explain("纸")
    assert "端砚" in explain("砚")
    assert explain("不存在") == ""


def test_overview():
    o = overview()
    assert "笔" in o and "墨" in o and "纸" in o and "砚" in o


def test_is_query_gating():
    assert is_scholar_query("文房四宝是什么")
    assert is_scholar_query("毛笔怎么养")
    assert is_scholar_query("砚台哪里的好")
    assert not is_scholar_query("今天天气好")
    assert not is_scholar_query("给我支笔")              # 要支笔、不是聊文房 → 不抢


def test_config_extra():
    cfg = {"scholar_tools": {"items": [["镇尺", ["镇尺"], "压纸的长条，铜的木的都有"]]}}
    assert "镇尺" in treasures(cfg)
    assert "压纸" in explain("镇尺", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ scholar_tools: all tests passed")
