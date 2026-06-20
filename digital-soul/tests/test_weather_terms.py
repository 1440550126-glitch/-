"""看懂天气预报测试。可直接运行：python tests/test_weather_terms.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.weather_terms import (  # noqa: E402
    count, explain, find_term, is_weather_term_query, terms,
)


def test_terms_present():
    ts = terms()
    for k in ("降水概率", "预警信号", "空气质量", "风力等级", "体感温度"):
        assert k in ts
    assert count() >= 8


def test_find_term_alias():
    assert find_term("下雨概率是啥") == "降水概率"
    assert find_term("AQI多少算好") == "空气质量"
    assert find_term("几级风算大") == "风力等级"
    assert find_term("今天天气好") is None


def test_explain_precip_is_probability():
    s = explain("降水概率")
    assert "可能" in s and "60%" in s          # 讲清是概率不是雨量
    assert explain("不存在") == ""


def test_warning_color_order():
    s = explain("预警信号")
    assert "蓝" in s and "红" in s and "最危险" in s   # 颜色轻重排序


def test_aqi_levels():
    s = explain("空气质量")
    assert "优" in s and "PM2.5" in s


def test_is_query_gating():
    assert is_weather_term_query("降水概率是什么意思")
    assert is_weather_term_query("红色预警严重吗")
    assert is_weather_term_query("空气质量多少算好")
    assert not is_weather_term_query("今天天气好")
    assert not is_weather_term_query("今天穿什么")          # 穿衣 → 留给 weather_day


def test_config_extra_term():
    cfg = {"weather_terms": {"terms": {"沙尘暴": "刮起来天黄、能见度低，关窗戴口罩别出门"}}}
    assert "沙尘暴" in terms(cfg)
    assert "口罩" in explain("沙尘暴", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ weather_terms: all tests passed")
