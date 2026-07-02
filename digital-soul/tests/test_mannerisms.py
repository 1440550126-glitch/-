"""说话习惯（神似）测试。可直接运行：python tests/test_mannerisms.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.mannerisms import (  # noqa: E402
    add_particle, address_for, apply_style, closer, describe, dialectize,
    load_mannerisms, opener,
)


def test_load_merges_config_and_identity():
    cfg = {"particles": ["嘛", "咯"], "dialect": {"知道": "晓得"},
           "address": {"孙子": "乖乖"}}
    idy = {"speech": {"particles": ["咯", "哈"], "openers": ["我跟你讲"],
                      "dialect": {"什么": "啥子"}}}
    m = load_mannerisms(cfg, idy)
    assert m["particles"] == ["嘛", "咯", "哈"]          # 去重保序
    assert m["openers"] == ["我跟你讲"]
    assert m["dialect"] == {"知道": "晓得", "什么": "啥子"}
    assert m["address"] == {"孙子": "乖乖"}


def test_address_for():
    m = {"address": {"孙子": "乖乖", "老伴": "老太婆"}}
    assert address_for(m, "孙子") == "乖乖"
    assert address_for(m, "老伴") == "老太婆"
    assert address_for(m, "陌生人") is None
    assert address_for({}, "孙子") is None


def test_dialectize_longest_first():
    m = {"dialect": {"知道": "晓得", "不知道": "莫得数"}}
    assert dialectize("我不知道", m) == "我莫得数"        # 长词优先，不被"知道"截断
    assert dialectize("我知道了", m) == "我晓得了"


def test_add_particle_skips_when_already_ended():
    m = {"particles": ["嘛"]}
    assert add_particle("好的", m) == "好的嘛"
    assert add_particle("好的。", m) == "好的。"          # 已有标点不加
    assert add_particle("好咯", m) == "好咯"              # 已有语气词不加
    assert add_particle("好的", {}) == "好的"             # 没配置原样返回


def test_apply_style_deterministic():
    m = {"particles": ["嘛", "咯"], "dialect": {"什么": "啥子"}}
    out = apply_style("你要什么", m)
    assert out.startswith("你要啥子")                     # 方言替换生效
    assert apply_style("你要什么", m) == out              # 同句两次结果一致（可单测）
    assert apply_style("随便说", None) == "随便说"        # 无习惯原样返回


def test_opener_closer():
    m = {"openers": ["我跟你讲", "话说回来"], "closers": ["就这样咯"]}
    assert opener(m, "abc") in m["openers"]
    assert closer(m) == "就这样咯"
    assert opener({}) is None


def test_describe():
    m = load_mannerisms({"particles": ["嘛"], "address": {"孙子": "乖乖"},
                         "dialect": {"知道": "晓得"}, "openers": ["我跟你讲"]})
    s = describe(m)
    assert "嘛" in s and "乖乖" in s and "晓得" in s and "我跟你讲" in s
    assert describe({}) == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ mannerisms: all tests passed")
