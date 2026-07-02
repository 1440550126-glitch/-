"""记忆遗忘曲线测试。可直接运行：python tests/test_forgetting.py"""

import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.forgetting import classify, importance, stability, strength  # noqa: E402
from dsoul.memory import Memory  # noqa: E402

DAY = 86400


def test_importance_emotion_and_tags():
    assert importance({"emotion": "深情"}) > importance({"emotion": "平静"})
    assert importance({"emotion": "平静", "tags": ["reflection"]}) >= 0.7
    assert importance({"emotion": "平静", "when": "2018"}) > importance({"emotion": "平静"})


def test_stability_grows_with_recalls():
    base = {"emotion": "平静"}
    assert stability({**base, "recalls": 5}) > stability(base)


def test_strength_decays_with_age():
    now = time.time()
    it = {"emotion": "平静", "created": now - 60 * DAY}
    fresh = {"emotion": "平静", "created": now}
    assert strength(it, now) < strength(fresh, now)
    # 情感深的同龄记忆衰减更慢
    deep = {"emotion": "深情", "created": now - 60 * DAY}
    assert strength(deep, now) > strength(it, now)


def test_recall_reinforces():
    now = time.time()
    it = {"emotion": "平静", "created": now - 60 * DAY}
    before = strength(it, now)
    it["recalls"], it["last_recall"] = 1, now          # 刚被回忆
    assert strength(it, now) > before
    assert classify(0.9) == "清晰" and classify(0.5) == "模糊" and classify(0.1) == "淡忘"


def test_memory_records_created_and_reinforce():
    m = Memory(tempfile.mktemp(suffix=".json"))
    mid = m.add("今天随便吃了碗面", source="x")
    it = next(i for i in m.items if i["id"] == mid)
    assert "created" in it and it.get("recalls", 0) == 0
    m.reinforce([mid])
    assert it["recalls"] == 1 and "last_recall" in it


def test_recall_is_strength_aware():
    from dsoul.agent import Agent
    a = object.__new__(Agent)
    m = Memory(tempfile.mktemp(suffix=".json"))
    old = m.add("我们一起去爬山看日出", source="x", emotion="平静")
    m.add("我们一起去爬山看星星", source="x", emotion="平静")
    for it in m.items:                                   # 让旧那条严重老化
        it["created"] = time.time() - (300 * DAY if it["id"] == old else 0)
    a.memory = m
    texts = [it["text"] for _, it in a._recall("一起去爬山", k=2)]
    assert texts and texts[0].endswith("星星")          # 新鲜的更易想起，排前


def test_rescue_fading_reinforces_important():
    from dsoul.agent import Agent
    a = object.__new__(Agent)
    m = Memory(tempfile.mktemp(suffix=".json"))
    mid = m.add("我和小婷的结婚纪念日", source="x", emotion="深情")  # 重要
    it = next(i for i in m.items if i["id"] == mid)
    it["created"] = time.time() - 120 * DAY                          # 但在淡忘
    a.memory = m
    assert mid in a.rescue_fading() and it["recalls"] == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ forgetting: all tests passed")
