"""老行当测试。可直接运行：python tests/test_old_trades.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.old_trades import (  # noqa: E402
    count, describe, find_trade, is_old_trade_query, recall, trades,
)


def test_trades_present():
    ts = trades()
    for k in ("剃头匠", "磨刀匠", "货郎", "爆米花", "弹棉花"):
        assert k in ts
    assert count() >= 12


def test_find_trade_alias_longest():
    assert find_trade("那个磨剪子戗菜刀的")[0] == "磨刀匠"
    assert find_trade("崩爆米花的来了")[0] == "爆米花"
    assert find_trade("摇拨浪鼓的")[0] == "货郎"
    assert find_trade("今天天气好") is None


def test_describe():
    d = describe("还记得剃头挑子吗")
    assert "剃头" in d and len(d) > 10
    assert describe("随便聊聊") == ""


def test_recall_opens_topic():
    s = recall(seed="y")
    assert "老行当" in s and "见过" in s


def test_recall_deterministic():
    assert recall(seed="z") == recall(seed="z")


def test_is_query_gating():
    assert is_old_trade_query("还记得剃头挑子吗")
    assert is_old_trade_query("聊聊老行当")
    assert is_old_trade_query("以前那个货郎")
    assert not is_old_trade_query("今天天气好")
    assert not is_old_trade_query("修鞋匠")                # 光提名字、没怀旧意图 → 不抢


def test_config_extra_trade():
    cfg = {"old_trades": {"items": [["染坊", ["染布"], "蓝印花布在大缸里一染一晾，整条河边挂得花花绿绿"]]}}
    assert "染坊" in trades(cfg)
    assert find_trade("染布的", cfg)[0] == "染坊"
    assert "花布" in describe("还记得染坊吗", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ old_trades: all tests passed")
