"""自然语言派活解析测试。可直接运行：python tests/test_dispatch.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.memory import Memory  # noqa: E402
from dsoul.remote_agents import parse_dispatch  # noqa: E402

NAMES = ["openclaw", "爱马仕"]


def test_command_with_name_and_verb():
    assert parse_dispatch("让openclaw把这周代码打个包", NAMES) == "openclaw"
    assert parse_dispatch("用爱马仕查下今天天气", NAMES) == "爱马仕"


def test_name_without_verb_is_chat():
    assert parse_dispatch("openclaw是什么东西", NAMES) is None


def test_no_name_is_chat():
    assert parse_dispatch("今天天气真不错", NAMES) is None


def test_empty():
    assert parse_dispatch("", NAMES) is None
    assert parse_dispatch("让它去办", []) is None


def test_is_affirm():
    assert Agent._is_affirm("好的，麻烦你") is True
    assert Agent._is_affirm("行，去吧") is True
    assert Agent._is_affirm("不用了") is False
    assert Agent._is_affirm("算了别弄了") is False


def test_pick_agent():
    assert Agent._pick_agent("周报还没写", NAMES) == "爱马仕"
    assert Agent._pick_agent("代码还没打包", NAMES) == "openclaw"
    assert Agent._pick_agent("随便干点啥", NAMES) == "openclaw"  # 无命中 → 第一个


def test_deed_written_to_memory():
    """成功派活 → 写进长期记忆 → 日后可被回忆/跟进。"""
    a = object.__new__(Agent)  # 只测记忆逻辑，不走完整构造
    a.memory = Memory(tempfile.mktemp(suffix=".json"))
    a._remember_deed("爱马仕", "这周的周报还没弄", "已生成周报.docx")
    hits = a.memory.recall("周报")
    assert hits and "爱马仕" in hits[0][1]["text"]
    deeds = a.recent_deeds()
    assert len(deeds) == 1 and "周报" in deeds[0]


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ dispatch: all tests passed")
