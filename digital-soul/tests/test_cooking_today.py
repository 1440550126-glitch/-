"""今天吃什么测试。可直接运行：python tests/test_cooking_today.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.cooking_today import season_of, suggest, what_to_eat  # noqa: E402


def test_season_of():
    assert season_of(4) == "春" and season_of(7) == "夏"
    assert season_of(10) == "秋" and season_of(1) == "冬"


def test_suggest_prefers_family():
    dish, kind = suggest(recipes=["红烧肉", "糖醋排骨"], season="冬")
    assert kind == "family" and dish in ("红烧肉", "糖醋排骨")


def test_suggest_avoids_allergy():
    dish, kind = suggest(recipes=["花生鸡丁"], season="春", avoid=["花生"])
    assert "花生" not in (dish or "")                    # 忌口的家传菜被跳过，回落时令


def test_suggest_season_fallback():
    dish, kind = suggest(recipes=[], season="夏")
    assert kind == "season" and dish in ("绿豆汤", "凉面", "拍黄瓜", "苦瓜炒蛋")


def test_what_to_eat():
    assert "老味道" in what_to_eat(recipes=["红烧肉"], season="冬")
    assert "应季" in what_to_eat(recipes=[], season="秋")
    assert "陪你张罗" in what_to_eat(recipes=["花生酥"], season="春", avoid=["花生"]) or \
        "应季" in what_to_eat(recipes=["花生酥"], season="春", avoid=["花生"])


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ cooking_today: all tests passed")
