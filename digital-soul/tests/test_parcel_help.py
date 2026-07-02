"""快递帮手测试。可直接运行：python tests/test_parcel_help.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.parcel_help import (  # noqa: E402
    count, find_topic, how_to, is_parcel_query, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("驿站取件", "快递柜取件", "寄快递", "签收验货", "查物流"):
        assert k in ts
    assert count() >= 5


def test_find_topic_alias():
    assert find_topic("菜鸟驿站怎么取") == "驿站取件"
    assert find_topic("丰巢怎么开") == "快递柜取件"
    assert find_topic("怎么邮寄东西") == "寄快递"
    assert find_topic("今天天气好") is None


def test_how_to_has_steps_and_tip():
    s = how_to("驿站取件")
    assert "取件码" in s and "提醒" in s
    assert how_to("不存在") == ""


def test_sign_for_warns_cod():
    s = how_to("签收验货")
    assert "货到付款" in s and ("拒收" in s or "确认是你买的" in s)


def test_logistics_has_phishing_warning():
    s = how_to("查物流")
    assert "官方" in s and ("钓鱼" in s or "别点" in s)       # 钓鱼链接提醒


def test_is_query_gating():
    assert is_parcel_query("驿站怎么取快递")
    assert is_parcel_query("快递柜怎么开")
    assert is_parcel_query("货到付款要验货吗")
    assert not is_parcel_query("今天天气好")
    assert not is_parcel_query("快递到了")                  # 陈述、不是问怎么办 → 不抢
    assert not is_parcel_query("快递到了吗")                # 没具体事项 → 不抢


def test_config_extra_topic():
    cfg = {"parcel_help": {"topics": {"代收点": ["小区门口小卖部代收，凭码取", "认准挂牌的代收点"]}}}
    assert "代收点" in topics(cfg)
    assert how_to("代收点", cfg).startswith("代收点：")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ parcel_help: all tests passed")
