"""养花知识测试。可直接运行：python tests/test_gardening.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.gardening import (  # noqa: E402
    care_for,
    find_plant,
    is_gardening_query,
    plants,
)


def test_plants_cover():
    ps = plants()
    for p in ("绿萝", "多肉", "君子兰", "茉莉"):
        assert p in ps


def test_care_for():
    assert "浇" in care_for("绿萝")
    assert "宁干勿湿" in care_for("多肉")
    assert care_for("不存在的花") == ""


def test_find_plant_alias_and_longest():
    assert find_plant("我的绿箩黄叶了") == "绿萝"        # 别名
    assert find_plant("多肉植物怎么养") == "多肉"
    assert find_plant("今天天气") == ""


def test_care_from_sentence():
    assert "君子兰" in care_for("君子兰怎么养")


def test_is_gardening_query():
    assert is_gardening_query("绿萝怎么养")
    assert is_gardening_query("多肉浇多少水")
    assert is_gardening_query("说点养花知识")
    assert is_gardening_query("我的茉莉叶子黄了")
    assert not is_gardening_query("今天几号")
    assert not is_gardening_query("绿萝真好看")          # 没问养护


def test_config_add():
    cfg = {"gardening": {"龟背竹": "喜散光，土干浇，叶子大要擦灰。"}}
    assert "龟背竹" in plants(cfg)
    assert "擦灰" in care_for("龟背竹怎么养", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ gardening: all tests passed")
