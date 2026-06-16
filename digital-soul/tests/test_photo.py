"""照片多模态测试。可直接运行：python tests/test_photo.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.photo import identify_faces, member_tags, photo_memory  # noqa: E402

FAMILY = {"members": [{"name": "外公", "relation": "姥爷"},
                      {"name": "外婆", "relation": "姥姥"}]}


def test_full_photo_memory():
    m = photo_memory(["小婷", "张爸"], when="2021", place="外婆家院子", caption="一起包饺子")
    assert m.startswith("（照片）")
    for piece in ["2021年", "外婆家院子", "包饺子", "小婷", "张爸"]:
        assert piece in m


def test_minimal_and_people_only():
    assert photo_memory() == "（照片）拍了一张照片。"
    assert "照片里有：豆豆" in photo_memory(["豆豆"])


def test_identify_faces_graceful():
    assert identify_faces(None, "x.jpg") == []          # 无视觉后端 → 空
    class _P:
        def identify(self, p):
            return "小婷"
    assert identify_faces(_P(), "x.jpg") == ["小婷"]


def test_member_tags_by_name_and_relation():
    tags = member_tags(["外公", "姥姥", "邻居老王"], FAMILY)
    assert tags == ["member:外公", "member:外婆"]      # 称呼"姥姥"也认作外婆；外人不归属


def test_member_tags_dedupes():
    assert member_tags(["外公", "姥爷"], FAMILY) == ["member:外公"]


class _Mem:
    def __init__(self):
        self.added = []

    def add(self, text, source="manual", tags=None, when=None, emotion=None):
        self.added.append({"text": text, "tags": tags or [], "when": when})
        return "id"


def test_agent_remember_photo_attributes_members():
    a = object.__new__(Agent)
    a.family = FAMILY
    a.memory = _Mem()
    text = a.remember_photo(["外公", "外婆", "邻居"], when="2021", caption="全家福")
    rec = a.memory.added[0]
    assert rec["text"] == text and "全家福" in text
    assert "member:外公" in rec["tags"] and "member:外婆" in rec["tags"]
    assert "photo" in rec["tags"] and rec["when"] == "2021"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ photo: all tests passed")
