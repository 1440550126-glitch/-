"""梦境生成测试。可直接运行：python tests/test_dream.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.dream import DreamLog, compose_dream  # noqa: E402

ITEMS = [
    {"id": "1", "text": "我和小婷在篮球场认识", "emotion": "深情", "created": 3},
    {"id": "2", "text": "小婷喜欢看我打篮球", "emotion": "深情", "created": 2},
    {"id": "3", "text": "我家有只金毛叫豆豆", "emotion": "平静", "created": 1},
]


def test_compose_dream_weaves_memories():
    d = compose_dream(ITEMS, mood="爱", names=["小婷"], seed=1)
    assert d and "梦" in d                                    # 含梦的底色/连接词
    assert any(k in d for k in ("篮球", "小婷", "豆豆"))         # 引用了记忆碎片


def test_too_few_memories_no_dream():
    assert compose_dream([{"id": "1", "text": "孤零零一条"}], seed=1) == ""


def test_excludes_dream_tagged():
    items = [{"id": "1", "text": "真实记忆", "tags": []},
             {"id": "2", "text": "一个旧梦", "tags": ["dream"]}]
    assert compose_dream(items, seed=1) == ""                 # 只剩 1 条非梦 → 不做梦


def test_dreamlog_persist_and_recent():
    p = tempfile.mktemp(suffix=".json")
    DreamLog(p).add("我梦见了大海", mood="喜")
    dl = DreamLog(p)
    assert dl.recent(1)[0]["text"] == "我梦见了大海" and dl.recent(1)[0]["mood"] == "喜"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ dream: all tests passed")
