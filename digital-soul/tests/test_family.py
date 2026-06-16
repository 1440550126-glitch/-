"""多人合一测试。可直接运行：python tests/test_family.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.family import (find_member, member_identity, members,  # noqa: E402
                          roster_line)
from dsoul.persona import Persona  # noqa: E402

FAMILY = {
    "members": [
        {"name": "外公", "relation": "姥爷", "catchphrases": ["慢慢来"],
         "greeting": "哎，是你呀，过来坐。"},
        {"name": "外婆", "relation": "姥姥", "catchphrases": ["吃了没？"]},
    ],
}


def test_members_skips_invalid():
    fam = {"members": [{"name": "甲"}, {"relation": "无名"}, "不是字典", {"name": ""}]}
    ms = members(fam)
    assert [m["name"] for m in ms] == ["甲"]


def test_roster_line_lists_everyone():
    line = roster_line(FAMILY)
    assert "外公（姥爷）" in line and "外婆（姥姥）" in line


def test_find_member_by_name_or_relation():
    assert find_member(FAMILY, "把外公叫来")["name"] == "外公"
    assert find_member(FAMILY, "我想和姥姥说说话")["name"] == "外婆"
    assert find_member(FAMILY, "谁都不是") is None


def test_member_identity_knows_others():
    idy = member_identity(FAMILY["members"][0], FAMILY)
    assert idy["name"] == "外公"
    assert "外婆" in idy["family_others"] and "外公" not in idy["family_others"]
    assert idy["personality"]["catchphrases"] == ["慢慢来"]


def test_persona_prompt_mentions_family():
    idy = member_identity(FAMILY["members"][0], FAMILY)
    sp = Persona(idy).system_prompt()
    assert "你家里还有" in sp and "外婆" in sp


def test_agent_become_and_restore():
    a = object.__new__(Agent)
    a.family = FAMILY
    a.identity = {"name": "张明"}
    a.persona = Persona(a.identity)
    a.active_member = None
    a._home_identity = a._home_persona = None

    hi = a.become("我想和外公说说话")
    assert "外公" in hi or "是你呀" in hi
    assert a.identity["name"] == "外公" and a.active_member == "外公"

    back = a.restore_home()
    assert a.identity["name"] == "张明" and a.active_member is None
    assert "张明" in back


def test_agent_family_roster():
    a = object.__new__(Agent)
    a.family = FAMILY
    assert "外公" in a.family_roster()


class _FakeMem:
    """recall 给两条同分记忆，让 _recall 的"在场加权"成为唯一变量。"""

    def __init__(self, items):
        self._items = items

    def recall(self, q, k=4):
        return [(0.5, it) for it in self._items]


def test_member_memory_boosted_when_active():
    gen = {"id": "g", "text": "一条共享记忆", "tags": []}
    mem = {"id": "m", "text": "外公的专属记忆", "tags": ["member:外公"]}
    a = object.__new__(Agent)
    a.memory = _FakeMem([gen, mem])

    a.active_member = None                       # 没人"在场"：同分，保持输入顺序
    assert a._recall("随便", k=2)[0][1]["id"] == "g"

    a.active_member = "外公"                       # 外公在场：TA 的记忆被加权到第一
    assert a._recall("随便", k=2)[0][1]["id"] == "m"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ family: all tests passed")
