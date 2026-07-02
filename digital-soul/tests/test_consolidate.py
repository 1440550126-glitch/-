"""睡眠巩固测试：对话 → 长期记忆。可直接运行：python tests/test_consolidate.py"""

import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.authority import Authority  # noqa: E402
from dsoul.consolidate import Consolidator  # noqa: E402
from dsoul.journal import Journal  # noqa: E402
from dsoul.memory import Memory  # noqa: E402

AUTH = Authority(
    {
        "trust_levels": {"owner": 100, "family": 80, "stranger": 0},
        "permissions": {},
        "people": [
            {"name": "张明", "relation": "本人", "trust": "owner"},
            {"name": "小婷", "relation": "老婆", "trust": "family"},
        ],
    }
)
IDENT = {"name": "张明", "aka": ["阿明"]}


def _setup():
    tmp = tempfile.mkdtemp()
    return (
        Memory(os.path.join(tmp, "index.json")),
        Journal(os.path.join(tmp, "journal.jsonl")),
    )


def test_salient_becomes_memory():
    mem, jr = _setup()
    jr.append({"speaker": "张明", "speaker_relation": "本人",
               "utterance": "我今天升职了，特别开心", "reply": "哈哈恭喜"})
    jr.append({"speaker": "张明", "speaker_relation": "本人",
               "utterance": "嗯", "reply": "嗯"})  # 太短 → 忽略
    rep = Consolidator(mem, jr, llm=None, identity=IDENT, authority=AUTH).run()
    assert rep["processed"] == 2
    texts = [it["text"] for it in mem.items]
    assert any("升职" in t for t in texts)
    assert "嗯" not in texts


def test_idempotent():
    mem, jr = _setup()
    jr.append({"speaker": "小婷", "speaker_relation": "老婆",
               "utterance": "周末我们约好去看电影", "reply": "好"})
    c = Consolidator(mem, jr, llm=None, identity=IDENT, authority=AUTH)
    c.run()
    n1 = len(mem.items)
    r2 = c.run()  # 再跑：不应重复学习
    assert r2["processed"] == 0
    assert len(mem.items) == n1


def test_third_person_prefix():
    mem, jr = _setup()
    jr.append({"speaker": "小婷", "speaker_relation": "老婆",
               "utterance": "我升职了，想请大家吃饭庆祝", "reply": "太好了"})
    Consolidator(mem, jr, llm=None, identity=IDENT, authority=AUTH).run()
    assert any("小婷" in it["text"] and "跟我说" in it["text"] for it in mem.items)


def test_empty_journal():
    mem, jr = _setup()
    rep = Consolidator(mem, jr, llm=None, identity=IDENT, authority=AUTH).run()
    assert rep == {"processed": 0, "learned": []}


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("PASS", _name)
    print("✅ consolidate: all tests passed")
