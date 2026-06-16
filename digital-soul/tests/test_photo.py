"""照片多模态测试。可直接运行：python tests/test_photo.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.photo import identify_faces, photo_memory  # noqa: E402


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


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ photo: all tests passed")
