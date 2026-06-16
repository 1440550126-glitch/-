"""网页只读展示（数字遗产 / 多人合一 / 守护惦记）测试。
可直接运行：python tests/test_webstatus.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.webstatus import PAGE, _legacy_family_care  # noqa: E402


class _StubAgent:
    """只带 webstatus 展示块用到的字段，不构造完整 Agent。"""

    def __init__(self, **kw):
        self.legacy = kw.get("legacy", {})
        self.family = kw.get("family", {})
        self.care = kw.get("care", {})
        self._chronicle = kw.get("chronicle", "")

    def life_chronicle(self):
        return self._chronicle


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


def test_page_has_new_cards():
    for marker in ("id=chronicle", "id=lastwords", "id=precepts",
                   "id=family", "id=care", "talkTo"):
        assert marker in PAGE, marker


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ webstatus: all tests passed")
