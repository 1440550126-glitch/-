"""价值观与抉择测试。可直接运行：python tests/test_values.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.values import deliberate, load_values, relevant_values  # noqa: E402


def test_relevant_values_detects():
    rv = dict(relevant_values("为了升职取消陪老婆的纪念日，该不该？"))
    assert "重视家人" in rv and "尽责担当" in rv          # 陪/老婆/纪念日 vs 升职


def test_family_beats_work():
    adv = deliberate("为了加班，该不该取消陪老婆过纪念日？")
    assert adv and "重视家人" in adv and "工作能再来" in adv     # 家人优先于工作


def test_guarded_note_when_protected_person():
    adv = deliberate("小婷生病了，我该不该请假照顾她？", guarded=["小婷"])
    assert "守护" in adv and "守护的人" in adv                  # 触发守护 + 守护对象提示


def test_non_dilemma_returns_empty():
    assert deliberate("今天天气真好") == ""


def test_config_override():
    vals = load_values({"values": {"信守原则": {"weight": 0.7, "keywords": ["原则", "底线"]}}})
    assert "信守原则" in vals and "重视家人" in vals             # 覆盖叠加在默认上


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ values: all tests passed")
