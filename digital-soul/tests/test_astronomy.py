"""认星空测试。可直接运行：python tests/test_astronomy.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.astronomy import (  # noqa: E402
    about,
    find_topic,
    is_astro_query,
    topics,
)


def test_topics():
    ts = topics()
    for t in ("北斗七星", "银河", "月食", "八大行星"):
        assert t in ts


def test_about():
    assert "北极星" in about("北斗七星")
    assert "牛郎" in about("银河") or "光带" in about("银河")
    assert about("黑洞工厂") == ""


def test_find_topic_alias():
    assert find_topic("北斗星怎么辨方向") == "北斗七星"   # 只含"北斗"别名
    assert find_topic("天河是什么") == "银河"            # 别名
    assert find_topic("贼星是啥") == "流星"
    assert find_topic("今天天气") == ""


def test_about_from_sentence():
    assert "影子" in about("月食怎么回事") or "地球" in about("月食怎么回事")


def test_is_astro_query():
    assert is_astro_query("北斗七星怎么找北极星")
    assert is_astro_query("教我认星空")
    assert is_astro_query("月食是怎么回事")
    assert not is_astro_query("今天几号")
    assert not is_astro_query("我看见一颗流星")          # 没问是什么


def test_config_add():
    cfg = {"astronomy": {"启明星": "天亮前东方那颗最亮的，其实是金星。"}}
    assert "启明星" in topics(cfg)
    assert "金星" in about("启明星是什么", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ astronomy: all tests passed")
