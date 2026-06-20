"""怀旧影视测试。可直接运行：python tests/test_classic_films.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.classic_films import (  # noqa: E402
    categories, count, films_in, find_category, find_title, is_film_query,
    recommend,
)


def test_categories_and_count():
    cats = categories()
    for k in ("革命战争", "名著改编", "武侠功夫", "国产动画"):
        assert k in cats
    assert count() >= 25


def test_find_category_alias():
    assert find_category("有没有打鬼子的老电影") == "革命战争"
    assert find_category("放个动画片") == "国产动画"
    assert find_category("想看武侠的") == "武侠功夫"
    assert find_category("黄梅戏那种") == "戏曲歌舞"
    assert find_category("今天天气好") is None


def test_films_have_fields():
    for cat in categories():
        for title, when, note in films_in(cat):
            assert title                                 # 至少有片名
    # 抽查经典在不在
    allt = [t for cat in categories() for t, _, _ in films_in(cat)]
    assert "西游记" in allt and "地道战" in allt


def test_find_title():
    f = find_title("小时候老看西游记")
    assert f and f[0] == "西游记"
    assert find_title("随便聊聊") is None


def test_recommend_formats():
    s = recommend("武侠", seed="x")
    assert "《" in s and "想看武侠" in s
    g = recommend(seed="y")                              # 不指定类型也能推
    assert "《" in g
    assert recommend("不存在类型") == ""


def test_recommend_dedup():
    s = recommend("国产动画", seed="z", n=3)
    titles = [seg for seg in s.split("《") if "》" in seg]
    names = [seg.split("》")[0] for seg in titles]
    assert len(names) == len(set(names))                 # 不重复


def test_is_film_query_gating():
    assert is_film_query("推荐几部老电影")
    assert is_film_query("有什么经典电视剧")
    assert is_film_query("放个老动画片")
    assert is_film_query("武侠片推荐")
    assert not is_film_query("今天天气好")
    assert not is_film_query("看电影吗")                  # 太泛、无怀旧/推荐意图


def test_config_extra_films():
    cfg = {"classic_films": {"科教": [["小蝌蚪找妈妈", "1960 动画", "水墨动画的开山之作"]]}}
    assert "科教" in categories(cfg)
    assert films_in("科教", cfg)[0][0] == "小蝌蚪找妈妈"


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ classic_films: all tests passed")
