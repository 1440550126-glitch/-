"""戏曲测试。可直接运行：python tests/test_opera.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.opera import (  # noqa: E402
    arias,
    detect_genre,
    famous,
    genres,
    is_opera_request,
    normalize_genre,
    recognize,
    sing_opera,
)


def test_genres():
    gs = genres()
    for g in ("京剧", "黄梅戏", "越剧", "豫剧", "评剧"):
        assert g in gs


def test_normalize_genre_alias():
    assert normalize_genre("京戏") == "京剧"
    assert normalize_genre("黄梅") == "黄梅戏"
    assert normalize_genre("河南梆子") == "豫剧"
    assert normalize_genre("火星戏") == ""


def test_arias_and_famous():
    assert any("苏三" in line for _t, line in arias("京剧"))
    f = famous("黄梅戏", seed="a")
    assert "黄梅戏" in f and "《" in f


def test_sing_opera_named():
    s = sing_opera("豫剧", seed="a")
    assert "豫剧" in s and "哼两句" in s


def test_sing_opera_unspecified():
    s = sing_opera(seed="x")
    assert "《" in s and "哼两句" in s


def test_recognize():
    assert recognize("树上的鸟儿成双对") == "黄梅戏《天仙配》"
    assert "京剧" in recognize("苏三离了洪洞县将身来在大街前")
    assert recognize("随便一句不是戏") == ""


def test_detect_genre():
    assert detect_genre("来段京剧") == "京剧"
    assert detect_genre("唱个黄梅戏") == "黄梅戏"
    assert detect_genre("聊聊天") == ""


def test_is_opera_request():
    assert is_opera_request("唱段戏听听")
    assert is_opera_request("来段京剧")
    assert is_opera_request("我想听戏")
    assert not is_opera_request("今天几号")


def test_config_adds_opera():
    cfg = {"opera": {"沪剧": [["《罗汉钱》", "我的家在东北松花江上"]]}}
    assert "沪剧" in genres(cfg)
    assert "罗汉钱" in famous("沪剧", config=cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ opera: all tests passed")
