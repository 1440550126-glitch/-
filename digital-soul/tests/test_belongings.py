"""找东西测试。可直接运行：python tests/test_belongings.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.belongings import Belongings, parse_put, parse_where  # noqa: E402


def _b(seed=None):
    return Belongings(pathlib.Path(tempfile.mkdtemp()) / "b.json", seed=seed)


def test_parse_put():
    assert parse_put("我把钥匙放在鞋柜上了") == ("钥匙", "鞋柜")
    assert parse_put("存折搁抽屉里") == ("存折", "抽屉")
    assert parse_put("今天天气不错") is None


def test_parse_where():
    assert parse_where("钥匙放哪了") == "钥匙"
    assert parse_where("我的老花镜呢") == "老花镜"
    assert parse_where("今天几号") is None


def test_put_and_where():
    b = _b()
    b.put("钥匙", "鞋柜")
    assert b.where("钥匙") == "鞋柜"
    assert b.where("车钥匙") == "鞋柜"                    # 模糊匹配
    assert b.where("没放过的东西") is None


def test_seed_and_describe():
    b = _b({"places": {"存折": "床头柜抽屉"}})
    assert b.where("存折") == "床头柜抽屉"
    assert "存折在床头柜抽屉" in b.describe()


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "b.json"
    Belongings(p).put("老花镜", "茶几上")
    assert Belongings(p).where("老花镜") == "茶几上"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ belongings: all tests passed")
