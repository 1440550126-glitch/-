"""我眼里的你测试。可直接运行：python tests/test_understanding.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.understanding import Understanding  # noqa: E402


def _u():
    return Understanding(pathlib.Path(tempfile.mkdtemp()) / "u.json")


def test_observe_tallies_concerns():
    u = _u()
    u.observe("小明", "最近老睡不好", emotion="哀")
    u.observe("小明", "昨晚又失眠了", emotion="哀")
    u.observe("小明", "钱不够花", emotion="惧")
    assert u.people["小明"]["count"] == 3
    assert u.top_concerns("小明", 1) == ["睡不好"]       # 出现两次最多


def test_dominant_mood_and_temper():
    u = _u()
    for _ in range(3):
        u.observe("小婷", "今天好开心", emotion="喜")
    assert u.dominant_mood("小婷") == "喜"
    assert "爱说爱笑" in u.portrait("小婷")


def test_familiarity_grows():
    u = _u()
    assert u.familiarity("生人") == "还在慢慢了解"
    for i in range(7):
        u.observe("老友", f"聊第{i}次", emotion="乐")
    assert u.familiarity("老友") == "渐渐熟了"


def test_portrait_weaves_concerns():
    u = _u()
    u.observe("张三", "睡不好", emotion="哀")
    u.observe("张三", "又失眠", emotion="哀")
    p = u.portrait("张三")
    assert "在我眼里" in p and "睡不好" in p and "越懂你" in p


def test_portrait_stranger():
    assert "还不算熟" in _u().portrait("陌生人")


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "u.json"
    Understanding(p).observe("小明", "睡不好", emotion="哀")
    assert Understanding(p).people["小明"]["count"] == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ understanding: all tests passed")
