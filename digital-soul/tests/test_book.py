"""家族册测试。可直接运行：python tests/test_book.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.book import dialogue_section, family_book_html, member_section  # noqa: E402

MEMBER = {"name": "外公", "relation": "姥爷", "summary": "一辈子的木匠",
          "traits": ["慈祥", "节俭"], "catchphrases": ["慢慢来"]}


def test_member_section_renders_all_fields():
    h = member_section(MEMBER, ["你那张小板凳是我做的"])
    assert "外公 · 姥爷" in h and "一辈子的木匠" in h
    assert "慈祥" in h and "慢慢来" in h and "小板凳" in h


def test_member_section_empty_is_graceful():
    h = member_section({"name": "谁"})
    assert "这一页还很空" in h


def test_dialogue_section_and_empty():
    h = dialogue_section([{"speaker": "外公", "text": "慢慢来"},
                          {"speaker": "外婆", "text": "吃了没"}])
    assert "外公" in h and "外婆" in h and "聊着" in h
    assert dialogue_section([]) == ""


def test_book_html_selfcontained():
    h = family_book_html("张家", [member_section(MEMBER, [])],
                         family_line="咱家有：外公。", dialogue="")
    assert h.startswith("<!doctype html>") and h.rstrip().endswith("</html>")
    assert "张家" in h and "外公" in h
    assert "http://" not in h and "<script" not in h
    assert "&lt;" in family_book_html("x", [member_section({"name": "<b>"}, [])])


def test_book_escapes_html():
    h = member_section({"name": "<img src=x>", "summary": "a<script>b"}, [])
    assert "<img src=x>" not in h and "<script>b" not in h


def test_agent_build_family_book():
    a = object.__new__(Agent)
    a.identity = {"name": "张明"}
    a.family = {"members": [MEMBER, {"name": "外婆", "relation": "姥姥",
                                     "catchphrases": ["吃了没"]}]}
    a.llm = type("L", (), {"available": False})()
    a.memory = type("M", (), {"items": [
        {"text": "外公做木工", "tags": ["member:外公"]},
        {"text": "无关记忆", "tags": []},
    ]})()
    h = a.build_family_book(topic="做饭")
    assert "张明家" in h and "外公" in h and "外婆" in h
    assert "外公做木工" in h                       # 专属记忆进了册
    assert "无关记忆" not in h
    assert "聊着" in h                             # 附了对谈


def test_member_memories_filters_by_tag():
    a = object.__new__(Agent)
    a.memory = type("M", (), {"items": [
        {"text": "甲", "tags": ["member:外公"]},
        {"text": "乙", "tags": ["member:外婆"]},
        {"text": "丙", "tags": []},
    ]})()
    assert a.member_memories("外公") == ["甲"]


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ book: all tests passed")
