"""体征记录测试。可直接运行：python tests/test_vitals.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.vitals import VitalsLog, detect_kind, flag  # noqa: E402


def _v():
    return VitalsLog(pathlib.Path(tempfile.mkdtemp()) / "v.json")


def test_detect_kind():
    assert detect_kind("量了血压140 90") == "血压"
    assert detect_kind("血糖6.5") == "血糖"
    assert detect_kind("体温37.5") == "体温"
    assert detect_kind("今天天气好") is None


def test_flag_ranges():
    assert "偏高" in flag("血压", "150/95")
    assert flag("血压", "120/80") == ""
    assert "偏高" in flag("血糖", "8.2")
    assert "发烧" in flag("体温", "38")
    assert flag("体温", "36.5") == ""


def test_parse_and_record_bp():
    v = _v()
    it = v.parse_and_record("量了血压 145 92", now=datetime(2026, 6, 18))
    assert it["kind"] == "血压" and it["value"] == "145/92"
    assert v.latest("血压")["value"] == "145/92"
    assert "偏高" in flag("血压", it["value"])           # 145/92 触发偏高提醒


def test_recent_and_describe():
    v = _v()
    v.parse_and_record("体重70", now=datetime(2026, 6, 1))
    v.parse_and_record("体重69.5", now=datetime(2026, 6, 8))
    assert len(v.recent("体重")) == 2
    assert "体重" in v.describe("体重")
    assert "还没记过血压" in v.describe("血压")


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "v.json"
    VitalsLog(p).parse_and_record("血糖6.0", now=datetime(2026, 6, 18))
    assert VitalsLog(p).latest("血糖")["value"] == 6.0 or VitalsLog(p).latest("血糖")["value"] == "6.0"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ vitals: all tests passed")
