"""吉祥寓意测试。可直接运行：python tests/test_auspicious.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.auspicious import (  # noqa: E402
    find_symbol,
    is_auspicious_query,
    meaning_of,
    symbols,
)


def test_symbols_cover():
    ss = symbols()
    for s in ("蝙蝠", "鱼", "葫芦", "牡丹"):
        assert s in ss


def test_meaning_of():
    assert "福" in meaning_of("蝙蝠")
    assert "余" in meaning_of("鱼")
    assert "福禄" in meaning_of("葫芦")
    assert meaning_of("二维码") == ""


def test_find_symbol_alias_longest():
    assert find_symbol("荷花的寓意") == "莲"            # 别名
    assert find_symbol("葫芦藤代表什么") == "葫芦藤"     # 长词优先
    assert find_symbol("今天天气") == ""


def test_meaning_from_sentence():
    assert "余" in meaning_of("鱼是什么寓意")


def test_is_auspicious_query():
    assert is_auspicious_query("蝙蝠的寓意")
    assert is_auspicious_query("为什么贴鱼")
    assert is_auspicious_query("吉祥图案有哪些")
    assert not is_auspicious_query("今天几号")
    assert not is_auspicious_query("我钓了条鱼")          # 没问寓意


def test_config_add():
    cfg = {"auspicious": {"金鱼": "金玉满堂。"}}
    assert "金鱼" in symbols(cfg)
    assert "金玉满堂" in meaning_of("金鱼的寓意", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ auspicious: all tests passed")
