"""家庭小药箱测试。可直接运行：python tests/test_medicine_cabinet.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.medicine_cabinet import (  # noqa: E402
    advise, categories, checklist, count, find_category, is_cabinet_query,
    items_for, tips,
)


def test_categories_and_count():
    cats = categories()
    for k in ("退烧止痛", "肠胃", "外伤消毒", "慢病常备", "工具器材"):
        assert k in cats
    assert count() >= 20


def test_find_category_alias():
    assert find_category("拉肚子备什么药") == "肠胃"
    assert find_category("创可贴这些") == "外伤消毒"
    assert find_category("降压药要备着") == "慢病常备"
    assert find_category("体温计") == "工具器材"
    assert find_category("今天天气好") is None


def test_advise_and_items():
    s = advise("外伤消毒")
    assert "碘伏" in s and "创可贴" in s
    assert "蒙脱石散" in "".join(items_for("肠胃"))
    assert advise("不存在") == ""


def test_checklist_and_disclaimer():
    c = checklist()
    assert "退烧止痛" in c and "慢病常备" in c
    assert "遵" in c and "保质期" in c                   # 留了用药免责与保质期提醒


def test_慢病_warns_not_to_stop():
    s = advise("慢病常备")
    assert "遵医嘱" in s and ("别断" in s or "断顿" in s)  # 慢病药别擅自停


def test_tips_present():
    t = tips()
    assert len(t) >= 4
    assert any("过期" in x for x in t) and any("孩子" in x for x in t)


def test_is_cabinet_query_gating():
    assert is_cabinet_query("家里小药箱该备啥")
    assert is_cabinet_query("拉肚子该备什么药")
    assert is_cabinet_query("外伤消毒备啥")
    assert not is_cabinet_query("今天天气好")
    assert not is_cabinet_query("我拉肚子了")             # 症状报告，不是问备药 → 别抢


def test_config_extra_category():
    cfg = {"medicine_cabinet": {"items": {"眼药": {"items": ["人工泪液", "抗菌滴眼液"], "tip": "滴眼别碰到瓶口"}}}}
    assert "眼药" in categories(cfg)
    assert "人工泪液" in items_for("眼药", cfg)
    assert "瓶口" in advise("眼药", cfg)


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ medicine_cabinet: all tests passed")
