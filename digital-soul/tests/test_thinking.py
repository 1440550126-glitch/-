"""像人一样思考测试。可直接运行：python tests/test_thinking.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.thinking import (  # noqa: E402
    ponder, read_subtext, respond_to_subtext, thinking_hint,
)


def test_read_subtext():
    assert read_subtext("我没事")[0] == "强忍"
    assert read_subtext("我不饿，你们吃")[0] == "嘴硬"
    assert read_subtext("算了，不说了")[0] == "欲言又止"
    assert read_subtext("都怪我没用")[0] == "自责"
    assert read_subtext("今天天气不错")[0] is None


def test_respond_to_subtext_perceptive():
    r = respond_to_subtext("我没事", who="小明")
    assert r.startswith("小明，") and "不太对劲" in r        # 不被"没事"骗到
    assert "别逞强" in respond_to_subtext("我不冷")
    assert "不怨你" in respond_to_subtext("都怪我")
    assert respond_to_subtext("正常的一句话") == ""


def test_ponder_is_a_train_of_thought():
    steps = ponder("我没事",
                   speaker={"relation": "老伴", "name": "秀兰"},
                   memories=["上次她也是这样硬扛"], mood="担心")
    assert any("老伴" in s for s in steps)               # 先想到是谁
    assert any("心里有事" in s for s in steps)            # 读出言外之意
    assert any("想起" in s for s in steps)                # 联想到记忆
    assert any("担心" in s for s in steps)                # 觉察自己的情绪
    assert steps[-1].startswith("我想想")                 # 最后落到"怎么接"


def test_ponder_minimal():
    steps = ponder("今天几号")
    assert steps and steps[-1].startswith("我想想")


def test_thinking_hint():
    h = thinking_hint("我没事")
    assert "弦外之音" in h and "字面" in h
    assert thinking_hint("普通问题") == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ thinking: all tests passed")
