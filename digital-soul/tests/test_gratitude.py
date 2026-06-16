"""感恩与遗憾测试。可直接运行：python tests/test_gratitude.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.gratitude import gratitudes, reflect, regrets  # noqa: E402

ITEMS = [
    {"text": "和小婷结婚那天", "emotion": "喜"},
    {"text": "孩子出生", "emotion": "爱"},
    {"text": "没能见爷爷最后一面", "emotion": "哀"},
    {"text": "和老友吵翻了", "emotion": "恶"},
    {"text": "（照片）一张合影", "emotion": "喜"},          # 照片不算
    {"text": "梦见大海", "emotion": "喜", "tags": ["dream"]},  # 梦不算
    {"text": "买了菜", "emotion": "惧"},                    # 中性情绪不归类
]


def test_gratitudes_and_regrets_classified():
    g = gratitudes(ITEMS)
    r = regrets(ITEMS)
    assert "和小婷结婚那天" in g and "孩子出生" in g
    assert "（照片）" not in "".join(g) and "大海" not in "".join(g)
    assert "没能见爷爷最后一面" in r and "和老友吵翻了" in r


def test_reflect_text():
    s = reflect(ITEMS)
    assert "最感念的" in s and "放不下的" in s
    assert "结婚" in s and "爷爷" in s


def test_reflect_empty():
    assert "知足" in reflect([])
    assert "知足" in reflect([{"text": "中性", "emotion": "惧"}])


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ gratitude: all tests passed")
