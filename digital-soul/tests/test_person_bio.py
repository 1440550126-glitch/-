"""人物小传测试。可直接运行：python tests/test_person_bio.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.person_bio import categorize, compose_bio, pronoun  # noqa: E402


def test_pronoun_by_relation():
    assert pronoun("老婆") == "她" and pronoun("妻子") == "她"
    assert pronoun("爸") == "他" and pronoun("儿子") == "他"
    assert pronoun("朋友") == "ta"


def test_categorize():
    c = categorize([
        "我和小婷2018年认识",          # milestone（含年份/认识）
        "我答应小婷去看极光",          # promise
        "我们一起养了只狗",            # shared
        "小婷做得一手好菜",            # trait
        "小婷喜欢蓝色",                # other? 含"喜欢"→trait（爱/喜欢在 _TRAIT 的"爱"? 不一定）
    ])
    assert "我和小婷2018年认识" in c["milestone"]
    assert "我答应小婷去看极光" in c["promise"]
    assert "我们一起养了只狗" in c["shared"]
    assert "小婷做得一手好菜" in c["trait"]


def test_compose_bio_warm_and_ordered():
    mems = [
        "我答应小婷，等退休了带她去看一次极光",
        "我和小婷是2018年在大学篮球场认识的",
        "小婷做得一手好川菜",
    ]
    bio = compose_bio("小婷", "老婆", mems)
    assert bio.startswith("小婷是我的老婆。")
    # 相识在承诺前（像传记不像流水账）
    assert bio.index("认识") < bio.index("答应")
    assert "她" in bio and "小婷" not in bio.split("。", 1)[1]   # 后文用代词
    assert bio.rstrip().endswith("收着。")                       # 暖心收尾


def test_kinship_pronoun_collapse():
    bio = compose_bio("张爸", "父亲", ["我爸张爸是退休老师"])
    assert "我爸是" in bio and "我爸他" not in bio               # "我爸他"收成"我爸"


def test_empty_when_no_memories():
    assert compose_bio("谁", "朋友", []) == ""
    assert compose_bio("谁", "朋友", ["  "]) == ""


def test_dedup_identical_memories():
    bio = compose_bio("小婷", "老婆", ["我和小婷散步", "我和小婷散步"])
    assert bio.count("散步") == 1


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ person_bio: all tests passed")
