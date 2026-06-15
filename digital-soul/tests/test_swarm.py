"""群体模拟预测测试。可直接运行：python tests/test_swarm.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.swarm import forecast  # noqa: E402


def test_optimistic_question_leans_yes():
    f = forecast("我有个好机会，挺想试试，把握也大，能成吗")
    assert f["p"] > 0.5 and f["yes"] >= f["no"]


def test_risky_question_leans_no():
    f = forecast("这事风险很大，又累又危险，还得熬夜拼命，靠谱吗")
    assert f["p"] < 0.5 and f["no"] >= f["yes"]


def test_report_has_panel_and_reasons():
    f = forecast("会不会成")
    assert "小会" in f["text"] and "个不同的我" in f["text"]
    assert f["yes"] + f["no"] + f["neutral"] == len(f["panel"])


def test_llm_panel_when_available():
    class _LLM:
        available = True

        def chat(self, system, q):
            return ("乐观派|会|机会好\n谨慎派|悬|有风险\n务实派|会|划算\n"
                    "重情派|观望|看情况\n守护派|悬|太累\n理性派|会|长远看不错")

    f = forecast("能成吗", llm=_LLM())
    assert f["yes"] == 3 and f["no"] == 2 and f["neutral"] == 1
    assert "机会好" in f["text"]                            # 用了大模型给的理由


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ swarm: all tests passed")
