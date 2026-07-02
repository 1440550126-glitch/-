"""声气测试。可直接运行：python tests/test_vocalics.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.vocalics import lead_cue, stage_note, voice_lead  # noqa: E402


def test_lead_cue_funny_is_speakable():
    c = lead_cue("我给你讲个笑话", emotion="乐")
    assert c == "嘿嘿，"
    assert "（" not in c                                  # 能读出来，不带括号


def test_lead_cue_sad():
    assert lead_cue("他走了好些年了", emotion="哀") == "唉……"
    assert lead_cue("随便一句", emotion="哀") == "唉……"   # 情绪也能触发


def test_lead_cue_tender():
    assert lead_cue("我一直想你", emotion=None) == "嗯……"
    assert lead_cue("乖，别累着", emotion="爱") == "嗯……"


def test_lead_cue_fear_reassure():
    assert lead_cue("别怕，有我在", emotion=None) == "别急，"


def test_lead_cue_greet():
    assert lead_cue("你来啦", emotion="喜") == "哎，"


def test_lead_cue_exclaim_fallback():
    # 没命中情绪词，但带感叹号 → 提口气
    assert lead_cue("快看那个！") == "哎呀，"


def test_lead_cue_none_for_plain():
    assert lead_cue("现在三点十分。") == ""


def test_stage_note_has_parens():
    s = stage_note("我给你讲个笑话", "乐")
    assert s.startswith("（") and s.endswith("）")


def test_voice_lead_prepends_cue():
    out = voice_lead("我给你讲个笑话", "乐")
    assert out.startswith("嘿嘿，")
    assert out.endswith("讲个笑话")


def test_voice_lead_no_double_when_already_leads():
    # 本来就以同样语气词开头，别叠一遍
    out = voice_lead("嘿嘿，这个真逗", "乐")
    assert out.count("嘿嘿") == 1


def test_voice_lead_plain_unchanged():
    assert voice_lead("现在三点十分。") == "现在三点十分。"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ vocalics: all tests passed")
