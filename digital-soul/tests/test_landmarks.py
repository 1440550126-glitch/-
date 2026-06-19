"""名山大川测试。可直接运行：python tests/test_landmarks.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.landmarks import (  # noqa: E402
    about,
    find_landmark,
    five_mountains,
    is_landmark_query,
    landmarks,
)


def test_landmarks_cover():
    ls = landmarks()
    for x in ("泰山", "长城", "故宫", "黄河"):
        assert x in ls


def test_about():
    assert "五岳之首" in about("泰山") or "东岳" in about("泰山")
    assert "皇宫" in about("故宫") or "紫禁城" in about("故宫")
    assert about("迪士尼") == ""


def test_find_alias():
    assert find_landmark("东岳是哪座山") == "泰山"
    assert find_landmark("紫禁城介绍") == "故宫"
    assert find_landmark("敦煌讲讲") == "莫高窟"
    assert find_landmark("今天天气") == ""


def test_five_mountains():
    fm = five_mountains()
    assert "泰山" in fm and "华山" in fm and "嵩山" in fm


def test_about_from_sentence():
    assert "长城" in about("长城在哪")


def test_is_landmark_query():
    assert is_landmark_query("五岳是哪五座")
    assert is_landmark_query("泰山在哪")
    assert is_landmark_query("故宫介绍一下")
    assert not is_landmark_query("今天几号")
    assert not is_landmark_query("我去过长城")           # 没问介绍


def test_config_add():
    cfg = {"landmarks": {"九寨沟": "在四川，五彩池水如童话。"}}
    assert "九寨沟" in landmarks(cfg)
    assert "五彩池" in about("九寨沟在哪", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ landmarks: all tests passed")
