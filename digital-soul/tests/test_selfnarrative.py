"""自我意识叙事测试。可直接运行：python tests/test_selfnarrative.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.selfnarrative import compose_self_narrative  # noqa: E402


def test_full_narrative_weaves_all_parts():
    t = compose_self_narrative(
        "张明", core_people=["小婷", "张爸"], mood_desc="心情愉悦",
        insight="家人最重要", cherished="和小婷的初遇", dream="梦见大海", traits="温和、重感情")
    assert "张明" in t
    for piece in ["小婷", "心情愉悦", "家人最重要", "和小婷的初遇", "大海", "温和"]:
        assert piece in t


def test_minimal_narrative_omits_missing():
    t = compose_self_narrative("阿宝")
    assert t.startswith("我是阿宝的数字分身。")
    assert "我最在乎" not in t and "怕淡忘" not in t          # 没有的部分不硬凑
    assert "会成长的镜子" in t                                 # 仍有收束句


def test_llm_path_used_when_available():
    class _LLM:
        available = True

        def chat(self, system, prompt):
            return "（大模型织就的自我认知）"

    t = compose_self_narrative("张明", core_people=["小婷"], llm=_LLM())
    assert t == "（大模型织就的自我认知）"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ selfnarrative: all tests passed")
