"""对话连贯测试。可直接运行：python tests/test_continuity.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.continuity import callback, recent_context_hint  # noqa: E402


def test_recent_context_hint():
    h = recent_context_hint(["我最近腰疼", "想去趟医院", "又怕花钱"])
    assert "腰疼" in h and "医院" in h and "接着这个话头" in h
    assert recent_context_hint([]) == ""


def test_recent_context_hint_keeps_last_k():
    h = recent_context_hint(["第一句", "第二句", "第三句", "第四句"], k=2)
    assert "第三句" in h and "第四句" in h and "第一句" not in h


def test_callback_finds_shared_word():
    c = callback("那医院远不远", ["我想去趟医院", "今天天气好"])
    assert "医院" in c and c.startswith("你刚还提到")


def test_callback_ignores_common_words():
    # 只共享"今天"这类常见词，不算回指
    assert callback("今天累不累", ["今天上班"]) == ""


def test_callback_none_when_unrelated():
    assert callback("吃饭了吗", ["我去爬山了"]) == ""


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ continuity: all tests passed")
