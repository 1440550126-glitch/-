"""传家页（家珍册）测试。可直接运行：python tests/test_heritage.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.agent import Agent  # noqa: E402
from dsoul.favors import FavorBook  # noqa: E402
from dsoul.heirloom import collect_heirlooms  # noqa: E402
from dsoul.heritage import (  # noqa: E402
    build_heritage, heritage_data, heritage_html,
)


def _agent():
    a = object.__new__(Agent)
    a.identity = {"name": "张伯"}
    a.family = {"members": [
        {"name": "张伯", "relation": "本人", "gen": 0},
        {"name": "小孙", "relation": "孙子", "birthday": "2015-06-20"},
    ]}
    a.heirlooms = collect_heirlooms({"heirlooms": [
        {"item": "怀表", "from": "你太爷", "story": "戴了三十年", "to": "小孙", "where": "抽屉"}]})
    a.health = {"conditions": [{"who": "张伯", "condition": "高血压", "note": "别贪咸"}],
                "allergies": [{"who": "小孙", "to": "花生"}]}
    a.stories = {"stories": [{"title": "苦日子", "story": "六零年挖野菜熬过来。"}]}
    a.teachings = {"lessons": [{"topic": "诚信", "lesson": "答应的事要办到。"}],
                   "skills": [{"name": "包饺子", "steps": ["和面", "调馅"], "note": "点三次水"}]}
    a.sayings = {"sayings": ["家和万事兴"]}
    a.recipes = {"recipes": [{"name": "红烧肉", "steps": ["焯水", "上色"]}]}
    a.legacy = {"last_words": ["好好吃饭"], "precepts": ["多回家"]}
    a.mannerisms = {"particles": ["咯"], "address": {}, "openers": [], "closers": [], "dialect": {}}
    a.spouse = {"name": "秀兰", "call": "老婆子", "met": "纺织厂相识",
                "story": ["1975 结婚"], "promises": ["一起看天安门"], "married": "1975-10-01",
                "endearments": [], "care": [], "self_call": "", "relation": "老伴", "rituals": []}
    a.memory = None
    fav = FavorBook(pathlib.Path(tempfile.mkdtemp()) / "f.json")
    fav.add("老王", 600, direction="收到")
    a.favors = fav
    return a


def test_heritage_data_gathers_all():
    d = heritage_data(_agent())
    assert d["name"] == "张伯"
    assert any(g["label"] == "孙辈" for g in d["genealogy"])
    assert d["heirlooms"][0]["item"] == "怀表"
    assert d["health"]["conditions"][0]["condition"] == "高血压"
    assert d["stories"][0]["title"] == "苦日子"
    assert d["teachings"]["lessons"][0]["topic"] == "诚信"
    assert "家和万事兴" in d["sayings"]
    assert "红烧肉" in d["recipes"]
    assert d["favors"]["we_owe"] == [("老王", 600)]
    assert "好好吃饭" in d["legacy"]["last_words"]


def test_heritage_data_degrades_on_bare_agent():
    bare = object.__new__(Agent)          # 什么都没有也不该炸
    d = heritage_data(bare)
    assert isinstance(d, dict) and d["genealogy"] == [] and d["heirlooms"] == []


def test_heritage_html_contains_sections():
    html = heritage_html(heritage_data(_agent()))
    for token in ["家珍册", "张伯", "家谱", "怀表", "苦日子", "诚信", "包饺子",
                  "红烧肉", "高血压", "老王", "家训", "我们", "纺织厂", "天安门"]:
        assert token in html, token
    assert html.strip().startswith("<!doctype html>")


def test_heritage_html_skips_empty():
    html = heritage_html({"name": "无名"})
    assert "还没有可展示" in html               # 全空时给友好占位


def test_build_heritage_writes_file():
    out = pathlib.Path(tempfile.mkdtemp()) / "heritage.html"
    p = build_heritage(_agent(), out)
    assert pathlib.Path(p).exists()
    assert "家珍册" in pathlib.Path(p).read_text(encoding="utf-8")


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ heritage: all tests passed")
