"""看出门道测试。可直接运行：python tests/test_observe.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.observe import observation, recurring_themes  # noqa: E402


def test_recurring_themes():
    utts = ["最近老是睡不好", "昨晚又失眠了", "今天天气不错", "钱不够花了"]
    themes = recurring_themes(utts, min_count=2)
    assert themes and themes[0][0] == "睡不好" and themes[0][1] == 2


def test_no_recurrence_below_threshold():
    assert recurring_themes(["睡不好", "钱紧"], min_count=2) == []   # 各一次，不够


def test_recurring_sorted_by_count():
    utts = ["好累", "太累了", "扛不住了", "失眠"]
    themes = dict(recurring_themes(utts, min_count=2))
    assert themes["太累"] == 3 and "睡不好" not in themes


def test_observation_perceptive():
    o = observation([("睡不好", 3)], name="小明")
    assert o.startswith("小明，") and "睡不好" in o and "憋着" in o
    assert observation([]) == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ observe: all tests passed")
