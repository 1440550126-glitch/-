"""急救信息卡测试。可直接运行：python tests/test_emergency_card.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.contacts import ContactBook  # noqa: E402
from dsoul.emergency_card import build_card, card_data, card_html, card_text  # noqa: E402
from dsoul.medication import MedBook  # noqa: E402


def _agent():
    a = object.__new__(Agent)
    a.identity = {"name": "张伯", "blood_type": "O型"}
    a.health = {"conditions": [{"who": "张伯", "condition": "高血压"},
                               {"who": "张伯", "condition": "糖尿病"}],
                "allergies": [{"who": "张伯", "to": "青霉素"}]}
    a.medications = MedBook(pathlib.Path(tempfile.mkdtemp()) / "m.json",
                            seed={"meds": [{"name": "降压药", "times": ["08:00"]}]})
    c = ContactBook(pathlib.Path(tempfile.mkdtemp()) / "c.json")
    c.add("小明", "13800000000", relation="儿子")
    a.contacts = c
    return a


def test_card_data():
    d = card_data(_agent())
    assert d["name"] == "张伯" and d["blood"] == "O型"
    assert "高血压" in d["conditions"] and "糖尿病" in d["conditions"]
    assert "青霉素" in d["allergies"]
    assert "降压药" in d["meds"]
    assert any("儿子" in c and "13800000000" in c for c in d["contacts"])


def test_card_text():
    t = card_text(card_data(_agent()))
    assert "急救信息卡" in t and "张伯" in t
    assert "高血压" in t and "青霉素" in t and "降压药" in t
    assert "120" in t


def test_card_html_and_build():
    a = _agent()
    html = card_html(card_data(a))
    assert html.strip().startswith("<!doctype html>")
    for tok in ("张伯", "高血压", "青霉素", "降压药", "儿子", "120"):
        assert tok in html, tok
    out = pathlib.Path(tempfile.mkdtemp()) / "card.html"
    build_card(a, out)
    assert out.exists() and "急救信息卡" in out.read_text(encoding="utf-8")


def test_degrades_on_bare_agent():
    d = card_data(object.__new__(Agent))
    assert isinstance(d, dict) and d["conditions"] == [] and d["meds"] == []


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ emergency_card: all tests passed")
