"""讲古 / 家庭故事会测试。可直接运行：python tests/test_storytelling.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.storytelling import (  # noqa: E402
    collect_stories, pick_story, tell, titles,
)

CFG = {"stories": [
    {"title": "怎么认识你奶奶", "story": "那年生产队插秧，她插得比谁都快。", "tags": ["奶奶", "年轻"]},
    {"title": "苦日子", "story": "六零年没粮，我们挖野菜熬过来的。", "tags": ["饥荒"]},
    "我十六岁就下矿了。",
]}


def test_collect_from_config_and_memory():
    mem = [{"text": "村里那座老桥是我修的。", "source": "story:bridge"},
           {"text": "今天天气不错。", "source": "diary"}]   # 非 story 的不收
    out = collect_stories(CFG, mem)
    stories = [s["story"] for s in out]
    assert "那年生产队插秧，她插得比谁都快。" in stories
    assert "村里那座老桥是我修的。" in stories
    assert "今天天气不错。" not in stories
    assert len(out) == 4


def test_pick_by_topic():
    out = collect_stories(CFG)
    s = pick_story(out, topic="奶奶")
    assert "插秧" in s["story"]


def test_pick_avoids_excluded():
    out = collect_stories(CFG)
    first = pick_story(out)
    second = pick_story(out, exclude=[first["story"]])
    assert second["story"] != first["story"]              # 轮着讲不重样


def test_tell_and_bedtime():
    s = {"title": "x", "story": "我们挖野菜熬过来的。", "tags": []}
    normal = tell(s)
    assert "挖野菜" in normal
    bed = tell(s, bedtime=True)
    assert "讲个故事" in bed or "慢慢讲" in bed
    assert tell(None) == ""


def test_titles():
    out = collect_stories(CFG)
    ts = titles(out)
    assert "怎么认识你奶奶" in ts
    assert any("…" in t for t in ts)                      # 无标题的截断显示


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ storytelling: all tests passed")
