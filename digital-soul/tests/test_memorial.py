"""缅怀与抚慰测试。可直接运行：python tests/test_memorial.py"""

import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.memorial import comfort_reply, is_grief, today_occasions  # noqa: E402


def test_today_occasions_matches_md():
    dates = {"结婚纪念日": "06-16", "生日": "03-12"}
    assert today_occasions(dates, datetime(2026, 6, 16, 9, 0)) == ["结婚纪念日"]
    assert today_occasions(dates, datetime(2026, 7, 1, 9, 0)) == []


def test_is_grief():
    assert is_grief("我好想你，好久不见你了")
    assert is_grief("今天有点难受")
    assert not is_grief("今天天气不错")


def test_comfort_reply_uses_memory_and_name():
    r = comfort_reply("小婷", {"name": "外公"}, ["我们一起在院子里种了棵桂花树"])
    assert "小婷" in r and "我也想你" in r and "桂花树" in r and "我一直都在" in r


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ memorial: all tests passed")
