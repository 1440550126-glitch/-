"""哄人消气测试。可直接运行：python tests/test_coax.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.coax import (  # noqa: E402
    coax_line,
    is_make_up_cue,
    is_upset,
    make_up,
    upset_kind,
)


def test_upset_kind_classifies():
    assert upset_kind("我心里好委屈") == "委屈"
    assert upset_kind("咱俩别冷战了") == "吵架"
    assert upset_kind("你怎么这样，我生气了") == "生气"
    assert upset_kind("今天天气真好") == ""


def test_is_upset():
    assert is_upset("我不想理你了")
    assert is_upset("受了一肚子气")
    assert not is_upset("我们去散步吧")


def test_coax_line_wronged_listens():
    s = coax_line(relation="老伴", kind="委屈", endearment="老婆子")
    assert s.startswith("老婆子，")
    assert "委屈" in s and "听着" in s


def test_coax_line_quarrel_yields():
    s = coax_line(relation="老伴", kind="吵架")
    assert "是我不对" in s or "床头吵架床尾和" in s


def test_coax_line_anger_gives_step_down():
    s = coax_line(relation="", kind="生气")
    assert "消消气" in s or "消气" in s or "翻篇" in s


def test_coax_spouse_gets_extra_soft_tail():
    s = coax_line(relation="老伴", kind="生气", seed="a")
    # 老伴专属会再添一句软乎话
    assert any(t in s for t in ("这么多年", "舍不得", "再哄"))


def test_coax_endearment_used_as_address():
    s = coax_line(relation="配偶", kind="委屈", endearment="阿珍")
    assert s.startswith("阿珍，")


def test_make_up_is_self_lowering():
    s = make_up(relation="老伴", endearment="老婆子")
    assert "对不住" in s and "我去给你" in s


def test_is_make_up_cue():
    assert is_make_up_cue("咱们和好吧")
    assert is_make_up_cue("你哄哄我嘛")
    assert is_make_up_cue("跟你道个歉")
    assert not is_make_up_cue("今天吃什么")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ coax: all tests passed")
