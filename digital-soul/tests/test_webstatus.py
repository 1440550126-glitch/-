"""网页只读展示（数字遗产 / 多人合一 / 守护惦记）测试。
可直接运行：python tests/test_webstatus.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.webstatus import (  # noqa: E402
    PAGE, _companion_guardian, _legacy_family_care,
)


class _StubAgent:
    """只带 webstatus 展示块用到的字段，不构造完整 Agent。"""

    def __init__(self, **kw):
        self.legacy = kw.get("legacy", {})
        self.family = kw.get("family", {})
        self.care = kw.get("care", {})
        self._chronicle = kw.get("chronicle", "")
        self.memory = kw.get("memory")

    def life_chronicle(self):
        return self._chronicle


class _Mem:
    def __init__(self, items):
        self.items = items


def test_empty_agent_degrades_gracefully():
    d = _legacy_family_care(_StubAgent())
    assert d["chronicle"] == "" and d["last_words"] == [] and d["precepts"] == []
    assert d["family"] == "" and d["family_members"] == [] and d["care"] == []


def test_legacy_surfaced():
    d = _legacy_family_care(_StubAgent(
        legacy={"last_words": ["好好吃饭"], "precepts": ["做人要诚实"]},
        chronicle="我这一生……"))
    assert d["last_words"] == ["好好吃饭"]
    assert d["precepts"] == ["做人要诚实"]
    assert d["chronicle"] == "我这一生……"


def test_family_surfaced():
    d = _legacy_family_care(_StubAgent(
        family={"members": [{"name": "外公", "relation": "姥爷"},
                            {"name": "外婆", "relation": "姥姥"}]}))
    assert "外公（姥爷）" in d["family"]
    assert [m["name"] for m in d["family_members"]] == ["外公", "外婆"]


def test_care_summarised_readonly():
    d = _legacy_family_care(_StubAgent(
        care={"妈": {"medicine": ["08:00", "20:00"], "checkup": "11-15", "note": "降压药"},
              "爸": {"medicine": "21:30"},
              "坏数据": "不是字典"}))
    joined = " | ".join(d["care"])
    assert "妈：降压药 08:00、20:00；复查 11-15" in joined
    assert "爸：药 21:30" in joined
    assert "坏数据" not in joined          # 非法项被跳过


def test_family_member_memory_counts():
    mem = _Mem([
        {"text": "外公的记忆1", "tags": ["member:外公"]},
        {"text": "外公的记忆2", "tags": ["member:外公"]},
        {"text": "共享记忆", "tags": []},
    ])
    d = _legacy_family_care(_StubAgent(
        family={"members": [{"name": "外公", "relation": "姥爷"},
                            {"name": "外婆", "relation": "姥姥"}]},
        memory=mem))
    by = {m["name"]: m["mem"] for m in d["family_members"]}
    assert by["外公"] == 2 and by["外婆"] == 0


def test_page_has_new_cards():
    for marker in ("id=chronicle", "id=lastwords", "id=precepts",
                   "id=family", "id=care", "talkTo",
                   "id=meds", "id=appts", "id=habits", "id=joys", "陪伴守护"):
        assert marker in PAGE, marker


class _CompanionAgent:
    """带陪伴守护字段的极简桩。"""

    class _Med:
        def reminders(self, now=None):
            return ["该吃降压药了，08:00 这顿别忘了。"]

    class _Appt:
        def upcoming(self, now=None, within=30):
            return [(2, {"date": "2026-06-20", "what": "复诊"})]

    class _Joy:
        def recent(self, k=3):
            return ["孙子来看我了"]

    def __init__(self):
        self.medications = self._Med()
        self.appointments = self._Appt()
        self.joys = self._Joy()
        self.habits_book = type("H", (), {"habits": {"早睡": {"streak": 5}}})()

    def muse(self):
        return "这会儿就盼着大家都顺顺当当。"


def test_companion_guardian_surfaced():
    d = _companion_guardian(_CompanionAgent())
    assert d["meds"] and "降压药" in d["meds"][0]
    assert d["appts"] == ["2026-06-20 复诊"]
    assert d["habits"] == ["早睡（连续5天）"]
    assert d["joys"] == ["孙子来看我了"]
    assert "顺顺当当" in d["muse"]


def test_companion_guardian_degrades():
    d = _companion_guardian(_StubAgent())          # 没有这些字段也不炸
    assert d == {"meds": [], "appts": [], "habits": [], "joys": [], "muse": ""}


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ webstatus: all tests passed")
