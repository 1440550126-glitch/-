"""家人多人对谈测试。可直接运行：python tests/test_converse.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.converse import extract_topic, family_dialogue  # noqa: E402

MEMBERS = [
    {"name": "外公", "relation": "姥爷", "catchphrases": ["慢慢来"],
     "memories": ["年轻时在木器厂当学徒"]},
    {"name": "外婆", "relation": "姥姥", "catchphrases": ["吃了没？"]},
]


def test_extract_topic_strips_names_and_verbs():
    assert extract_topic("让外公和外婆聊聊做饭", MEMBERS) == "做饭"
    assert extract_topic("外公跟姥姥唠唠", MEMBERS) == "家常"      # 没话题 → 家常


def test_heuristic_dialogue_each_voice_and_alternation():
    turns = family_dialogue(MEMBERS, "做饭", llm=None, rounds=2)
    assert len(turns) == 4                                   # 2 人 × 2 轮
    assert [t["speaker"] for t in turns] == ["外公", "外婆", "外公", "外婆"]
    assert turns[0]["text"].startswith("慢慢来")              # 外公的口头禅
    assert "吃了没" in turns[1]["text"]                       # 外婆的口头禅
    assert "木器厂" in turns[0]["text"]                       # 用上了外公的记忆
    assert "做饭" in turns[0]["text"]


def test_needs_two_people():
    assert family_dialogue(MEMBERS[:1], "做饭") == []
    assert family_dialogue([], "做饭") == []


class _LLM:
    available = True

    def chat(self, system, prompt):
        return "外公：慢慢来，火候要稳。\n外婆：吃了没？我去下碗面。\n旁白：（不该出现）"


def test_llm_dialogue_parsed_and_filtered():
    turns = family_dialogue(MEMBERS, "做饭", llm=_LLM(), rounds=1)
    assert [t["speaker"] for t in turns] == ["外公", "外婆"]   # 旁白被过滤
    assert "火候" in turns[0]["text"]


class _DeadLLM:
    available = True

    def chat(self, system, prompt):
        raise RuntimeError("down")


def test_llm_failure_falls_back_to_heuristic():
    turns = family_dialogue(MEMBERS, "做饭", llm=_DeadLLM(), rounds=1)
    assert len(turns) == 2 and turns[0]["speaker"] == "外公"


def test_agent_let_them_talk_and_finder():
    a = object.__new__(Agent)
    a.family = {"members": MEMBERS}
    a.llm = type("L", (), {"available": False})()
    assert [m["name"] for m in a.find_family_members("让外公和外婆聊聊")] == ["外公", "外婆"]
    out = a.let_them_talk("让外公和外婆聊聊做饭")
    assert "外公：" in out and "外婆：" in out
    assert a.let_them_talk("只有外公") == ""                  # 不足两人


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ converse: all tests passed")
