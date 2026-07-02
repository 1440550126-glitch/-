"""社交记忆测试。可直接运行：python tests/test_social.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.social import SocialLog  # noqa: E402

DAY = 86400


def test_warmth_moves_with_emotion_and_persists():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "s.json"
        s = SocialLog(p)
        r = s.note("小婷", emotion="爱", topic="极光", now=1000)
        assert r["warmth"] > 0.5 and r["count"] == 1 and r["topics"] == ["极光"]
        s.note("老王", emotion="怒", now=1000)
        assert s.record("老王")["warmth"] < 0.5
        assert SocialLog(p).record("小婷")["count"] == 1      # 持久化


def test_topics_capped_and_deduped():
    with tempfile.TemporaryDirectory() as d:
        s = SocialLog(pathlib.Path(d) / "s.json")
        for t in ["a", "b", "c", "d", "e", "f", "a"]:
            s.note("X", topic=t, now=1)
        tp = s.record("X")["topics"]
        assert len(tp) == 5 and tp[-1] == "a" and tp.count("a") == 1


def test_warmest_and_cooled():
    with tempfile.TemporaryDirectory() as d:
        s = SocialLog(pathlib.Path(d) / "s.json")
        s.note("亲", emotion="爱", now=100 * DAY)
        s.note("疏", emotion="怒", now=100 * DAY)
        s.note("老友", emotion="喜", now=10 * DAY)         # 很久没见
        assert s.warmest(1)[0][0] == "亲"
        cooled = dict(s.cooled(days=14, now=100 * DAY))
        assert "老友" in cooled and "亲" not in cooled


def test_describe():
    with tempfile.TemporaryDirectory() as d:
        s = SocialLog(pathlib.Path(d) / "s.json")
        assert "还没怎么打过交道" in s.describe("陌生人")
        for _ in range(5):
            s.note("小婷", emotion="爱", topic="散步", now=1)
        desc = s.describe("小婷")
        assert "小婷" in desc and "很亲" in desc and "散步" in desc


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ social: all tests passed")
