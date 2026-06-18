"""重要联系人测试。可直接运行：python tests/test_contacts.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.contacts import ContactBook  # noqa: E402


def _book(seed=None):
    return ContactBook(pathlib.Path(tempfile.mkdtemp()) / "c.json", seed=seed)


SEED = {"contacts": [
    {"name": "小明", "relation": "儿子", "phone": "13800000000"},
    {"name": "王医生", "relation": "医生", "phone": "010-12345"},
    {"name": "老李", "relation": "邻居", "phone": "13900000000"},
    {"name": "理发店", "relation": "", "phone": "555"},
]}


def test_seed_and_find():
    b = _book(SEED)
    assert b.find("给儿子打电话")["name"] == "小明"
    assert b.find("王医生")["phone"] == "010-12345"
    assert b.find("不认识的人") is None


def test_emergency_contacts():
    b = _book(SEED)
    ec = [c["name"] for c in b.emergency_contacts()]
    assert "小明" in ec and "王医生" in ec and "老李" in ec
    assert "理发店" not in ec                            # 非紧急
    line = b.emergency_line()
    assert "儿子" in line and "13800000000" in line


def test_describe_and_persist():
    p = pathlib.Path(tempfile.mkdtemp()) / "c.json"
    b1 = ContactBook(p, seed=SEED)
    assert "小明" in b1.describe()
    b2 = ContactBook(p)
    assert len(b2.items) == 4


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ contacts: all tests passed")
