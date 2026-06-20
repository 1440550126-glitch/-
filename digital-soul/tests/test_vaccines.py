"""老人疫苗测试。可直接运行：python tests/test_vaccines.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.vaccines import (  # noqa: E402
    count, find_vaccine, info, is_vaccine_query, overview, vaccines,
)


def test_vaccines_present():
    vs = vaccines()
    for k in ("流感疫苗", "肺炎疫苗", "带状疱疹疫苗", "破伤风疫苗"):
        assert k in vs
    assert count() >= 4


def test_find_vaccine_alias():
    assert find_vaccine("缠腰龙疫苗该打吗") == "带状疱疹疫苗"
    assert find_vaccine("流感针多久打") == "流感疫苗"
    assert find_vaccine("今天天气好") is None


def test_info_has_when_and_disclaimer():
    s = info("流感疫苗")
    assert "秋天" in s and "每年" in s
    assert "医生" in s or "接种点" in s              # 免责
    assert info("不存在") == ""


def test_shingles_for_50plus():
    s = info("带状疱疹疫苗")
    assert "50" in s and ("缠腰龙" in s or "神经痛" in s)


def test_overview():
    o = overview()
    assert "流感" in o and "肺炎" in o and "带状疱疹" in o


def test_is_query_gating():
    assert is_vaccine_query("流感疫苗该打吗")
    assert is_vaccine_query("老人打什么疫苗")
    assert is_vaccine_query("破伤风什么时候打")
    assert not is_vaccine_query("今天天气好")
    assert not is_vaccine_query("我打过疫苗了")       # 陈述、没问 → 不抢


def test_config_extra_vaccine():
    cfg = {"vaccines": {"items": {"狂犬疫苗": ["被猫狗咬抓伤后尽快打，按程序打几针", "伤口先冲洗消毒"]}}}
    assert "狂犬疫苗" in vaccines(cfg)
    assert "冲洗" in info("狂犬疫苗", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ vaccines: all tests passed")
