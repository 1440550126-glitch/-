"""情书测试。可直接运行：python tests/test_loveletter.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.loveletter import (  # noqa: E402
    _heuristic_letter, compose_love_letter, letter_html,
)
from dsoul.spouse import spouse_profile  # noqa: E402

CFG = {
    "name": "秀兰", "call": "老婆子", "self_call": "老头子",
    "met": "1972年在纺织厂", "married": "1975-10-01",
    "story": ["1972 相识", "1975 结婚"],
    "promises": ["一起去看天安门"],
    "endearments": ["娶到你是我的福气", "你笑我就安心"],
}


def test_heuristic_letter_structure():
    p = spouse_profile(CFG)
    letter = _heuristic_letter(p, memories=["你给我织的那条围巾"], occasion="纪念日")
    assert letter.startswith("老婆子：")               # 开头唤昵称
    assert "纺织厂" in letter                          # 用了相识素材
    assert "天安门" in letter                          # 用了约定
    assert "围巾" in letter                            # 用了记忆
    assert "老头子" in letter                          # 落款
    assert "结婚纪念日" in letter


def test_compose_falls_back_without_llm():
    p = spouse_profile(CFG)
    letter = compose_love_letter(p, identity={"name": "老周"}, llm=None)
    assert "老婆子" in letter and letter == _heuristic_letter(p, None, "")


def test_compose_uses_llm_when_available():
    class FakeLLM:
        available = True
        def chat(self, system, user):
            assert "老婆子" in system                  # 把昵称喂进了提示
            return "老婆子，见字如面。——老头子"
    letter = compose_love_letter(spouse_profile(CFG), llm=FakeLLM())
    assert letter == "老婆子，见字如面。——老头子"


def test_compose_llm_failure_falls_back():
    class BadLLM:
        available = True
        def chat(self, system, user):
            raise RuntimeError("down")
    letter = compose_love_letter(spouse_profile(CFG), llm=BadLLM())
    assert "老婆子：" in letter                         # 异常时退回模板


def test_no_profile_empty():
    assert compose_love_letter({}) == ""
    assert _heuristic_letter(None) == ""


def test_letter_html():
    p = spouse_profile(CFG)
    html = letter_html("老婆子：\n见字如面。", p)
    assert html.strip().startswith("<!doctype html>")
    assert "见字如面" in html and "<br>" in html        # 换行转成 <br>


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ loveletter: all tests passed")
