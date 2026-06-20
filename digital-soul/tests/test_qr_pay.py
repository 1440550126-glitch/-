"""付款码/收款码安全测试。可直接运行：python tests/test_qr_pay.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.qr_pay import (  # noqa: E402
    advice, count, find_topic, is_qr_query, overview, topics,
)


def test_topics_present():
    ts = topics()
    for k in ("付款码", "收款码", "区别", "安全设置", "丢手机", "扫码防骗"):
        assert k in ts
    assert count() >= 6


def test_find_topic_alias():
    assert find_topic("付款码和收款码怎么分") == "区别"
    assert find_topic("手机丢了咋办") == "丢手机"
    assert find_topic("陌生二维码能扫吗") == "扫码防骗"
    assert find_topic("今天天气好") is None


def test_payment_code_never_share():
    s = advice("付款码")
    assert "扫" in s and ("绝不" in s or "送出去" in s or "别" in s)


def test_difference_clear():
    s = advice("区别")
    assert "花钱" in s and "收钱" in s


def test_lost_phone_freeze():
    s = advice("丢手机")
    assert "挂失" in s or "冻结" in s


def test_overview_and_scam():
    o = overview()
    assert "付款码" in o and "收款码" in o and ("骗局" in o or "别扫" in o)


def test_is_query_gating():
    assert is_qr_query("付款码和收款码有什么区别")
    assert is_qr_query("手机丢了支付怎么办")
    assert is_qr_query("扫码领红包安全吗")
    assert not is_qr_query("今天天气好")


def test_config_extra_topic():
    cfg = {"qr_pay": {"topics": {"刷脸支付": ["对准摄像头、确认金额", "陌生设备别随便刷脸"]}}}
    assert "刷脸支付" in topics(cfg)
    assert "金额" in advice("刷脸支付", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ qr_pay: all tests passed")
