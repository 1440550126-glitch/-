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


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ swarm: all tests passed")
