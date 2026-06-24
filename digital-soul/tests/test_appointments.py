"""就医/约定提醒测试。可直接运行：python tests/test_appointments.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.appointments import AppointmentBook  # noqa: E402


def _book(seed=None):
    return AppointmentBook(pathlib.Path(tempfile.mkdtemp()) / "appt.json", seed=seed)


SEED = {"appointments": [
    {"date": "2026-06-20", "what": "复诊", "where": "市医院"},
    {"date": "2026-07-15", "what": "体检", "where": "体检中心"},
]}


def test_seed_and_sorted():
    b = _book(SEED)
    assert [it["date"] for it in b.items] == ["2026-06-20", "2026-07-15"]


def test_upcoming_within():
    b = _book(SEED)
    up = b.upcoming(datetime(2026, 6, 18), within=14)
    assert len(up) == 1 and up[0][0] == 2 and up[0][1]["what"] == "复诊"


def test_reminders_with_prep():
    b = _book(SEED)
    lines = b.reminders(datetime(2026, 6, 19), within=3)        # 复诊在明天
    assert any("明天" in s and "复诊" in s for s in lines)
    assert any("医保卡" in s for s in lines)                    # 复诊该带的东西


def test_add_md_only_and_persist():
    p = pathlib.Path(tempfile.mkdtemp()) / "appt.json"
    b1 = AppointmentBook(p)
    assert b1.add("12-25", "打疫苗", note="带身份证")
    b2 = AppointmentBook(p)
    assert b2.items[0]["what"] == "打疫苗"
    assert b2.add("乱写", "x") is None                          # 非法日期不收


def test_describe():
    # 传定值 now，别让真实时钟漂移把固定日期的安排"过期"掉
    assert "复诊" in _book(SEED).describe(now=datetime(2026, 6, 19))
    assert "没排什么事" in _book().describe(now=datetime(2026, 6, 19))


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ appointments: all tests passed")
