"""说出我的感受测试。可直接运行：python tests/test_express_feelings.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.express_feelings import is_feeling_query, share_feeling  # noqa: E402


def test_share_feeling_by_mood():
    assert "亮堂" in share_feeling("喜") or "跟着乐" in share_feeling("喜")
    assert "难受" in share_feeling("哀") or "担着" in share_feeling("哀")
    assert "来气" in share_feeling("怒") or "窝火" in share_feeling("怒")


def test_share_feeling_neutral_fallback():
    s = share_feeling(None)
    assert "平静" in s or "安安稳稳" in s
    assert share_feeling("没这情绪")                      # 未知也有兜底


def test_share_feeling_deterministic():
    assert share_feeling("喜", seed="k") == share_feeling("喜", seed="k")


def test_is_feeling_query():
    assert is_feeling_query("你现在什么心情")
    assert is_feeling_query("你开心吗")
    assert not is_feeling_query("今天几号")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ express_feelings: all tests passed")
