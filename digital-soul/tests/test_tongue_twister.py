"""绕口令测试。可直接运行：python tests/test_tongue_twister.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.tongue_twister import (  # noqa: E402
    all_twisters,
    by_keyword,
    by_level,
    count,
    is_twister_request,
    random_one,
    wants_hard,
)


def test_count_and_all():
    assert count() >= 10
    assert any("葡萄" in t for t in all_twisters())


def test_random_one_deterministic():
    assert random_one("aa") == random_one("aa")     # 同 seed 同结果
    assert random_one("x")                          # 非空


def test_by_keyword():
    assert "葡萄" in by_keyword("葡萄那个怎么说")
    assert "四" in by_keyword("四是四那条")
    assert by_keyword("查无此词的绕口令xyz") == ""


def test_by_level():
    easy = by_level(1, seed="a")
    assert easy in all_twisters()
    hard = by_level(3, seed="a")
    assert hard in all_twisters()


def test_by_level_fallback_when_absent():
    assert by_level(9, seed="a")                    # 没有该难度 → 兜底随便来一条


def test_is_twister_request():
    assert is_twister_request("来个绕口令")
    assert is_twister_request("练练嘴")
    assert not is_twister_request("今天几号")


def test_wants_hard():
    assert wants_hard("来个难的绕口令")
    assert wants_hard("上难度")
    assert not wants_hard("来个简单的")


def test_config_adds_twister():
    cfg = {"tongue_twisters": ["自家的绕口令一二三", {"text": "带难度的", "level": 3, "keys": ["难度"]}]}
    assert "自家的绕口令一二三" in all_twisters(cfg)
    assert by_keyword("难度那条", cfg) == "带难度的"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ tongue_twister: all tests passed")
