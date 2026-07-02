"""防蚊虫叮咬测试。可直接运行：python tests/test_bug_bites.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.bug_bites import (  # noqa: E402
    advice, bugs, count, find_bug, is_bite_query, overview,
)


def test_bugs_present():
    bs = bugs()
    for k in ("蚊子", "蜂蜇", "蜱虫", "隐翅虫"):
        assert k in bs
    assert count() >= 5


def test_find_bug_alias():
    assert find_bug("草爬子咬了") == "蜱虫"
    assert find_bug("被马蜂蜇了") == "蜂蜇"
    assert find_bug("洋辣子蜇的") == "毛毛虫"
    assert find_bug("今天天气好") is None


def test_bee_sting_anaphylaxis_120():
    s = advice("蜂蜇")
    assert "毒刺" in s and "120" in s and ("呼吸困难" in s or "过敏" in s)


def test_tick_dont_yank():
    s = advice("蜱虫")
    assert "别硬拔" in s and "镊子" in s and ("发烧" in s or "传染病" in s)


def test_rove_beetle_dont_smash():
    s = advice("隐翅虫")
    assert ("别拍死" in s or "吹走" in s) and "冲" in s


def test_overview():
    o = overview()
    assert "蚊子" in o and "蜱虫" in o and "120" in o


def test_is_query_gating():
    assert is_bite_query("蚊子咬了怎么止痒")
    assert is_bite_query("被马蜂蜇了怎么办")
    assert is_bite_query("隐翅虫能拍吗")
    assert not is_bite_query("今天天气好")
    assert not is_bite_query("有只蚊子")               # 陈述、没问 → 不抢


def test_config_extra_bug():
    cfg = {"bug_bites": {"bugs": {"蚂蟥": ["别硬扯，拍打周围让它松口或撒盐", "伤口压迫止血"]}}}
    assert "蚂蟥" in bugs(cfg)
    assert "撒盐" in advice("蚂蟥", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ bug_bites: all tests passed")
