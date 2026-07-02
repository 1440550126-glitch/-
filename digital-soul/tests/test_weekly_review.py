"""一周回望测试。可直接运行：python tests/test_weekly_review.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.weekly_review import compose, is_review_query  # noqa: E402


def test_compose_weaves_all():
    s = compose(joys=["孙子来看我了"], concerns=["睡不好"], habits=[("早睡", 5)])
    assert "孙子来看我了" in s
    assert "早睡坚持了5天" in s
    assert "睡不好" in s
    assert "往前走" in s


def test_compose_empty_is_warm():
    s = compose()
    assert "安安稳稳就是福" in s and "回望" in s


def test_compose_skips_zero_streak():
    s = compose(habits=[("锻炼", 0)])
    assert "锻炼" not in s                                # 没坚持起来的不提


def test_is_review_query():
    assert is_review_query("这周过得怎么样")
    assert is_review_query("回顾这周")
    assert not is_review_query("今天几号")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ weekly_review: all tests passed")
