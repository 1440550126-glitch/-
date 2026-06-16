"""说话风格层测试。可直接运行：python tests/test_style.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.style import apply_style, style_hint  # noqa: E402

ID = {"name": "外公", "personality": {
    "speaking_style": "慢条斯理，爱讲老理儿",
    "catchphrases": ["乖乖", "莫慌"],
    "particles": ["嘛", "撒"]}}


def test_style_hint_mentions_voice_and_catchphrases():
    h = style_hint(ID)
    assert "外公" in h and "乖乖" in h and "嘛" in h


def test_style_hint_empty_when_no_persona():
    assert style_hint({"name": "x"}) == ""


def test_apply_style_adds_voice():
    out = apply_style("天冷了，记得加衣服。", ID, seed=1)
    assert "天冷了" in out                                 # 原意保留
    assert any(c in out for c in ID["personality"]["catchphrases"]) or \
           any(p in out for p in ID["personality"]["particles"])   # 染上口吻


def test_apply_style_skips_questions_and_no_double_catchphrase():
    assert apply_style("你吃饭了吗？", ID, seed=1).endswith("吗？")        # 问句不乱加
    out = apply_style("乖乖，早点睡。", ID, seed=2)
    assert out.count("乖乖") == 1                          # 已有口头禅不重复加


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ style: all tests passed")
