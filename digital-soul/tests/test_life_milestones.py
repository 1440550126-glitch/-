"""人生节点寄语测试。可直接运行：python tests/test_life_milestones.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.life_milestones import (  # noqa: E402
    blessing,
    detect_milestone,
    for_utterance,
    milestones,
)


def test_milestones_cover():
    ms = milestones()
    for m in ("高考", "结婚", "生子", "退休", "创业"):
        assert m in ms


def test_detect_basic():
    assert detect_milestone("我下个月要高考了") == "高考"
    assert detect_milestone("我要结婚了") == "结婚"
    assert detect_milestone("我退休了") == "退休"
    assert detect_milestone("今天天气不错") == ""


def test_detect_prefers_longer_cue():
    # "换工作"应胜过"工作"
    assert detect_milestone("我想换工作了") == "换工作"
    assert detect_milestone("我入职新公司了") == "工作"


def test_blessing_has_name_and_wisdom():
    b = blessing("高考", name="囡囡")
    assert b.startswith("囡囡，")
    assert "尽力" in b


def test_blessing_unknown_empty():
    assert blessing("查无此节点") == ""


def test_for_utterance():
    s = for_utterance("我要创业开公司了", name="小明")
    assert s.startswith("小明，")
    assert "留条退路" in s
    assert for_utterance("随便聊聊") == ""


def test_failure_milestone():
    assert detect_milestone("我被裁了") == "失业"
    assert "天塌不下来" in blessing("失业")


def test_config_override():
    cfg = {"milestones": {"高考": "爷爷的话：沉住气，发挥出来就行。"}}
    assert "爷爷的话" in blessing("高考", config=cfg)
    # 覆盖了文字，触发词仍在
    assert detect_milestone("我要高考了", cfg) == "高考"


def test_config_add_new_with_cues():
    cfg = {"milestones": {"乔迁": {"cues": ["搬家", "乔迁"], "words": "搬新家，添添喜气。"}}}
    assert detect_milestone("我们要搬家了", cfg) == "乔迁"
    assert "添添喜气" in blessing("乔迁", config=cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ life_milestones: all tests passed")
