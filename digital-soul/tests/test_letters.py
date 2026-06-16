"""代笔家书测试。可直接运行：python tests/test_letters.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.letters import compose_letter  # noqa: E402


def test_template_letter_structure():
    s = compose_letter("张明", catchphrases=["好好的，比什么都强"], recipient_name="小婷",
                       recipient_relation="老婆", occasion="生日",
                       memories=["我们在篮球场认识"])
    assert s.startswith("亲爱的小婷：")
    assert "生日" in s
    assert "篮球场" in s
    assert "好好的，比什么都强" in s
    assert s.rstrip().endswith("张明  字")


def test_occasion_unknown_uses_default_line():
    s = compose_letter("李", recipient_name="阿明", occasion="搬家")   # 不在表里
    assert "见字如面" in s and s.startswith("亲爱的阿明：")


def test_no_memories_ok():
    s = compose_letter("王", recipient_name="儿子")
    assert "亲爱的儿子：" in s and "字" in s


class _LLM:
    available = True

    def __init__(self):
        self.seen = None

    def chat(self, system, prompt):
        self.seen = (system, prompt)
        return "亲爱的小婷：\n想你了。\n张明"


def test_llm_letter_used_when_available():
    llm = _LLM()
    s = compose_letter("张明", catchphrases=["哈哈"], recipient_name="小婷",
                       occasion="想念", memories=["篮球场"], llm=llm)
    assert s == "亲爱的小婷：\n想你了。\n张明"
    assert "想念" in llm.seen[1] and "篮球场" in llm.seen[1]


class _DeadLLM:
    available = True

    def chat(self, s, p):
        raise RuntimeError("x")


def test_llm_failure_falls_back():
    s = compose_letter("张明", recipient_name="小婷", llm=_DeadLLM())
    assert s.startswith("亲爱的小婷：")            # 回落到模板


def test_agent_write_letter_and_occasion():
    a = object.__new__(Agent)
    a.identity = {"name": "张明", "personality": {"catchphrases": ["好好的"]}}
    a.llm = type("L", (), {"available": False})()

    class _Auth:
        def resolve(self, n):
            return {"known": True, "name": n, "relation": "老婆"}
    a.authority = _Auth()
    a.memory = type("M", (), {"items": []})()
    a._recall = lambda q, k=4: [(0.9, {"text": "我们在篮球场认识"})]

    s = a.write_letter("小婷", occasion=a._letter_occasion("给小婷写封生日信"))
    assert "亲爱的小婷：" in s and "生日" in s and "篮球场" in s
    assert a._letter_occasion("写封信") is None


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ letters: all tests passed")
