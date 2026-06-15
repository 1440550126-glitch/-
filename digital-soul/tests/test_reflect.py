"""自主反思测试。可直接运行：python tests/test_reflect.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.memory import Memory  # noqa: E402
from dsoul.reflect import Reflector  # noqa: E402


class _Journal:
    """最小日记桩：只需 _all()。"""

    def __init__(self, entries):
        self.entries = entries

    def _all(self):
        return self.entries


_ENTRIES = [
    {"speaker": "小婷", "utterance": "今天好开心，我升职了"},
    {"speaker": "小婷", "utterance": "老板当众表扬我，特别开心"},
    {"speaker": "小婷", "utterance": "这周天天加班，好累"},
    {"speaker": "小婷", "utterance": "又要加班，烦死了"},
]


def _mem():
    return Memory(tempfile.mktemp(suffix=".json"))


def test_heuristic_reflection_writes_insights():
    m = _mem()
    r = Reflector(m, _Journal(_ENTRIES), identity={"name": "张明"})
    insights = r.reflect()
    assert len(insights) >= 2                                  # 多条维度的领悟
    assert any("小婷" in s for s in insights)                   # 认出最常相处的人
    assert any(("开心" in s or "加班" in s) for s in insights)   # 认出高频话题
    # 领悟已写进长期记忆，并带 reflection 标签
    tagged = [it for it in m.items if "reflection" in it.get("tags", [])]
    assert len(tagged) == len(insights)


def test_reflection_not_duplicated():
    m = _mem()
    r = Reflector(m, _Journal(_ENTRIES), identity={"name": "张明"})
    first = r.reflect()
    again = r.reflect()           # 同样的经历，不该重复"悟"
    assert first and again == []


def test_too_few_experiences_no_reflection():
    m = _mem()
    r = Reflector(m, _Journal(_ENTRIES[:2]), identity={"name": "张明"})
    assert r.reflect() == []


def test_tick_reflects_when_due_then_quiet():
    m = _mem()
    a = object.__new__(Agent)     # 只测心跳逻辑，不走完整构造
    a.memory = m
    a.journal = _Journal(_ENTRIES)
    a.reflector = Reflector(m, a.journal, identity={"name": "张明"})
    a._reflect_every = 3
    a._last_reflect_len = 0
    a.tasks = None
    a.hub = None
    out1 = a.tick()
    assert out1["reflections"] and out1["notices"]
    out2 = a.tick()               # 没有新经历 → 不再反思
    assert out2["reflections"] == []


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ reflect: all tests passed")
