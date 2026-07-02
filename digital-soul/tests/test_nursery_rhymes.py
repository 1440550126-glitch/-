"""童谣测试。可直接运行：python tests/test_nursery_rhymes.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.nursery_rhymes import (  # noqa: E402
    find,
    get,
    is_rhyme_request,
    random_rhyme,
    rhymes,
)


def test_rhymes_cover():
    rs = rhymes()
    assert "小老鼠上灯台" in rs and "拔萝卜" in rs and "两只老虎" in rs


def test_get():
    assert "偷油吃" in get("小老鼠上灯台")
    assert "嘿哟" in get("拔萝卜")
    assert get("查无此谣") == ""


def test_find_alias_and_longest():
    assert find("念个小老鼠的童谣") == "小老鼠上灯台"
    assert find("乖乖那个怎么念") == "小兔子乖乖"      # 别名
    assert find("今天天气") == ""


def test_get_from_sentence():
    assert "两只老虎" in get("两只老虎怎么念")


def test_random_rhyme():
    r = random_rhyme(seed="x")
    assert "《" in r and "：" in r


def test_is_rhyme_request():
    assert is_rhyme_request("念个童谣")
    assert is_rhyme_request("来首儿歌")
    assert is_rhyme_request("拔萝卜怎么念")
    assert not is_rhyme_request("今天几号")
    assert not is_rhyme_request("两只老虎在动物园")     # 没念/唱意图


def test_config_add():
    cfg = {"nursery_rhymes": {"小燕子": "小燕子，穿花衣，年年春天来这里。"}}
    assert "小燕子" in rhymes(cfg)
    assert "穿花衣" in get("小燕子", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ nursery_rhymes: all tests passed")
