"""缴费帮手测试。可直接运行：python tests/test_pay_bills.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.pay_bills import (  # noqa: E402
    bills, count, find_bill, general, how_to, is_pay_query,
)


def test_bills_present():
    bs = bills()
    for k in ("电费", "水费", "燃气费", "话费", "物业费"):
        assert k in bs
    assert count() >= 6


def test_find_bill_alias():
    assert find_bill("煤气费在哪交") == "燃气费"
    assert find_bill("怎么充话费") == "话费"
    assert find_bill("交网费") == "宽带费"
    assert find_bill("今天天气好") is None


def test_how_to_has_where_online_offline_antiscam():
    s = how_to("电费")
    assert "用户编号" in s and "线上" in s and "线下" in s
    assert "别点" in s and "骗局" in s              # 防骗叮嘱在
    assert how_to("不存在") == ""


def test_general_overview():
    g = general()
    assert "线上" in g and "线下" in g and "户号" in g


def test_is_pay_query_gating():
    assert is_pay_query("电费怎么交")
    assert is_pay_query("水费在哪交")
    assert is_pay_query("缴费怎么弄")
    assert not is_pay_query("今天天气好")
    assert not is_pay_query("记一笔电费100")        # 记账 → 不抢
    assert not is_pay_query("提醒我交电费")          # 设提醒 → 不抢


def test_config_extra_bill():
    cfg = {"pay_bills": {"bills": {"停车费": ["物业小程序或停车场扫码交", "月卡更划算"]}}}
    assert "停车费" in bills(cfg)
    assert how_to("停车费", cfg).startswith("交停车费：")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ pay_bills: all tests passed")
