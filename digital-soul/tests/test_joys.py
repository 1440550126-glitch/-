"""小确幸日记测试。可直接运行：python tests/test_joys.py"""

import pathlib
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.joys import JoyLog, evening_prompt, is_sharing_joy  # noqa: E402


def _log():
    return JoyLog(pathlib.Path(tempfile.mkdtemp()) / "joy.json")


def test_is_sharing_joy():
    assert is_sharing_joy("今天升职了好开心")
    assert is_sharing_joy("孙子来看我了，真高兴")
    assert not is_sharing_joy("今天开心吗")            # 疑问不算
    assert not is_sharing_joy("今天不开心")            # 反向不算
    assert not is_sharing_joy("把灯关了")


def test_add_strips_prefix_and_recent():
    b = _log()
    b.add("今天，孙子来看我了")
    b.add("我今天买菜遇到老朋友")
    assert b.count() == 2
    r = b.recent(2)
    assert r[0] == "买菜遇到老朋友"                     # 最新在前、去掉"我今天"
    assert "孙子来看我了" in r[1]


def test_reflect_and_acknowledge():
    b = _log()
    assert "今天有啥乐子" in b.reflect()                # 空时引导
    b.add("孙子考了一百分")
    assert "孙子考了一百分" in b.reflect()
    assert "记下了" in b.acknowledge("今天天气真好")


def test_evening_prompt_time_gated():
    assert "开心的小事" in evening_prompt(datetime(2026, 6, 18, 20))
    assert evening_prompt(datetime(2026, 6, 18, 10)) == ""


def test_persistence():
    p = pathlib.Path(tempfile.mkdtemp()) / "joy.json"
    JoyLog(p).add("中了个小奖")
    assert JoyLog(p).count() == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ joys: all tests passed")
