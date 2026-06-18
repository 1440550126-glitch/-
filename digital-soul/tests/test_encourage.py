"""打气测试。可直接运行：python tests/test_encourage.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.encourage import (  # noqa: E402
    detect_occasion, encourage, followup_question,
)


def test_detect_occasion():
    assert detect_occasion("我明天要考试了") == "考试"
    assert detect_occasion("下午有个面试好紧张") == "面试"
    assert detect_occasion("要上台演讲") == "演讲"
    assert detect_occasion("明天动手术") == "手术"
    assert detect_occasion("今天天气不错") is None


def test_encourage_tailored():
    e = encourage("我明天考试", name="小明")
    assert e.startswith("小明，") and ("别紧张" in e or "稳稳" in e)
    assert "手术" not in encourage("我去面试")          # 不串场合
    assert encourage("随便聊聊") == ""                   # 非场合返回空


def test_encourage_no_name():
    e = encourage("要比赛了")
    assert e and not e.startswith("，")


def test_followup():
    assert "考得怎么样" in followup_question("考试")
    assert "惦记" in followup_question("手术")
    assert followup_question("未知") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ encourage: all tests passed")
