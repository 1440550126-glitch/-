"""家庭账本测试。可直接运行：python tests/test_household_ledger.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.household_ledger import Ledger, is_money_record  # noqa: E402


def _ledger():
    return Ledger(pathlib.Path(tempfile.mkdtemp()) / "l.json")


def test_is_money_record():
    assert is_money_record("今天买菜花了30")
    assert is_money_record("领了退休金3000")
    assert not is_money_record("今天买菜了")            # 没数字
    assert not is_money_record("现在30度")              # 没收支词


def test_parse_and_record():
    led = _ledger()
    it = led.parse_and_record("今天买菜花了30", now=datetime(2026, 6, 18))
    assert it["kind"] == "支" and it["amount"] == 30 and it["category"] == "买菜"
    it2 = led.parse_and_record("领了退休金3000", now=datetime(2026, 6, 1))
    assert it2["kind"] == "收" and it2["amount"] == 3000
    assert led.parse_and_record("没有数字") is None


def test_month_summary():
    led = _ledger()
    led.parse_and_record("退休金3000", now=datetime(2026, 6, 1))
    led.parse_and_record("买菜花了30", now=datetime(2026, 6, 2))
    led.parse_and_record("看病花了200", now=datetime(2026, 6, 3))
    s = led.month_summary("2026-06")
    assert s["income"] == 3000 and s["expense"] == 230
    assert s["balance"] == 2770
    assert s["by_category"]["医药"] == 200


def test_describe_month():
    led = _ledger()
    led.parse_and_record("工资5000", now=datetime(2026, 6, 1))
    led.parse_and_record("打车花了40", now=datetime(2026, 6, 2))
    d = led.describe_month("2026-06")
    assert "进账 5000" in d and "花掉 40" in d and "交通40" in d
    assert "还没记什么账" in led.describe_month("2026-01")


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "l.json"
    Ledger(p).parse_and_record("买菜花了20", now=datetime(2026, 6, 1))
    assert len(Ledger(p).items) == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ household_ledger: all tests passed")
