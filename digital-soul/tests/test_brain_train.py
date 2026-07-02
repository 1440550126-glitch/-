"""动动脑测试。可直接运行：python tests/test_brain_train.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.brain_train import (  # noqa: E402
    a_drill,
    check,
    is_brain_train,
    math_drill,
    number_span,
    odd_one_out,
    proverb_fill,
)


def test_math_drill_correct():
    q, a = math_drill("seed1")
    assert "等于几" in q
    # 用题面里的数字验算
    import re
    nums = list(map(int, re.findall(r"\d+", q)))
    x, y = nums[0], nums[1]
    expect = x + y if "加" in q else x - y
    assert a == str(expect)


def test_number_span_reverses():
    q, a = number_span("abc")
    import re
    shown = re.findall(r"\d", q)
    assert a == "".join(reversed(shown))           # 答案是倒序连写
    assert " " not in a


def test_odd_one_out_answer_in_question():
    q, a = odd_one_out("z")
    assert a in q and "不是一类" in q


def test_proverb_fill():
    q, a = proverb_fill("p")
    assert "补全" in q and a


def test_a_drill_shape():
    kind, q, a = a_drill("k")
    assert kind and q and a
    assert a_drill("k") == a_drill("k")            # 同 seed 稳定


def test_check_lenient():
    assert check("32", "32")
    assert check("等于 32 吧", "32")
    assert check("9 1 8 3", "9183")                # 空格无所谓
    assert check("板凳", "板凳")
    assert not check("不知道", "一见")


def test_is_brain_train():
    assert is_brain_train("陪我动动脑")
    assert is_brain_train("来个记性操")
    assert is_brain_train("练练脑子")
    assert not is_brain_train("今天几号")


def test_drills_deterministic_but_varied():
    seeds = [str(i) for i in range(8)]
    qs = {a_drill(s)[1] for s in seeds}
    assert len(qs) >= 4                             # 不同 seed 多有变化


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ brain_train: all tests passed")
