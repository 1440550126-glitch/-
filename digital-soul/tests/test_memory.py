"""记忆检索测试：能否根据问题找回最相关的记忆。

可直接运行：python tests/test_memory.py
"""

import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.memory import Memory, cosine  # noqa: E402


def _fresh_memory() -> Memory:
    tmp = tempfile.mkdtemp()
    return Memory(os.path.join(tmp, "index.json"))


def test_recall_finds_relevant():
    m = _fresh_memory()
    m.add("我最喜欢的运动是打篮球，每个周末都去球场")
    m.add("我老婆叫小婷，我们是在大学篮球场认识的")
    m.add("我做了十年软件工程师，写后端")
    top = m.recall("我老婆是谁", k=1)
    assert top, "应当至少召回一条记忆"
    assert "小婷" in top[0][1]["text"]


def test_recall_empty_when_no_overlap():
    m = _fresh_memory()
    m.add("今天成都下雨了")
    assert m.recall("量子计算的退相干", k=3) == []


def test_dedup():
    m = _fresh_memory()
    m.add("重复的一句话")
    m.add("重复的一句话")
    assert len(m.items) == 1


def test_persist_and_reload():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "index.json")
    Memory(path).add("退休后带小婷去看极光")
    again = Memory(path)  # 重新加载
    assert len(again.items) == 1
    assert again.recall("极光", k=1)


def test_cosine_basic():
    assert cosine({"a": 1.0}, {"a": 1.0}) == 1.0
    assert cosine({"a": 1.0}, {"b": 1.0}) == 0.0


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("PASS", _name)
    print("✅ memory: all tests passed")
