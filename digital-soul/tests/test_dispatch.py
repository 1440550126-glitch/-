"""自然语言派活解析测试。可直接运行：python tests/test_dispatch.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

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


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ dispatch: all tests passed")
