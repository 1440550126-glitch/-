"""垃圾分类：'西瓜皮是什么垃圾''过期药怎么扔'——常见东西归哪一类，问一声就清楚。
四分类：厨余（湿）/ 可回收 / 有害 / 其他（干）。各地叫法略有差别，按通行说法来。

纯数据 + 纯逻辑、可单测。可在 config 加本地的归类。
"""

from __future__ import annotations

# 物品 → 类别
_ITEMS = {
    # 厨余（湿垃圾）
    "剩饭": "厨余", "剩菜": "厨余", "果皮": "厨余", "西瓜皮": "厨余", "菜叶": "厨余",
    "果核": "厨余", "蛋壳": "厨余", "茶叶渣": "厨余", "咖啡渣": "厨余", "鱼刺": "厨余",
    "小骨头": "厨余", "瓜子壳": "厨余", "剩饭剩菜": "厨余", "过期食品": "厨余", "花卉": "厨余",
    # 可回收
    "塑料瓶": "可回收", "矿泉水瓶": "可回收", "易拉罐": "可回收", "纸箱": "可回收",
    "报纸": "可回收", "书": "可回收", "玻璃瓶": "可回收", "旧衣服": "可回收",
    "纸板": "可回收", "金属": "可回收", "饮料瓶": "可回收", "快递盒": "可回收",
    "旧家电": "可回收", "易拉罐子": "可回收",
    # 有害
    "电池": "有害", "纽扣电池": "有害", "过期药": "有害", "药品": "有害", "灯管": "有害",
    "荧光灯": "有害", "水银温度计": "有害", "温度计": "有害", "油漆桶": "有害",
    "杀虫剂": "有害", "指甲油": "有害", "废胶片": "有害", "染发剂": "有害",
    # 其他（干垃圾）
    "烟头": "其他", "餐巾纸": "其他", "卫生纸": "其他", "尿不湿": "其他", "大骨头": "其他",
    "贝壳": "其他", "陶瓷": "其他", "陶瓷碎片": "其他", "一次性筷子": "其他", "笔": "其他",
    "灰土": "其他", "毛发": "其他", "破碗": "其他", "猫砂": "其他",
}

_CATEGORY = {
    "厨余": ("厨余垃圾（湿垃圾）", "容易腐烂的食物残渣，拿去堆肥或单独处理。"),
    "可回收": ("可回收物", "干净、能再利用的——纸、塑料、玻璃、金属、布料。"),
    "有害": ("有害垃圾", "对人或环境有害，要单独投放——电池、药品、灯管、化学品。"),
    "其他": ("其他垃圾（干垃圾）", "既不能回收也不易腐烂的，扔进其他垃圾桶。"),
}

_ALIAS = {"瓶子": "塑料瓶", "饭": "剩饭", "纸盒": "纸箱", "废电池": "电池",
          "旧报纸": "报纸", "可乐瓶": "塑料瓶", "纸巾": "餐巾纸"}


def _table(config) -> dict:
    db = dict(_ITEMS)
    if isinstance(config, dict) and isinstance(config.get("garbage"), dict):
        for k, v in config["garbage"].items():
            cat = str(v).strip()
            if cat in _CATEGORY:
                db[str(k).strip()] = cat
    return db


def categories() -> list:
    return [v[0] for v in _CATEGORY.values()]


def find_item(query, config=None) -> str:
    """从一句话里认出是哪样东西（含别名），命中最长的。"""
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for name in db:
        if name in u and len(name) > blen:
            best, blen = name, len(name)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def sort(item, config=None) -> str:
    """这东西归哪类 + 一句缘由。认不出返回空。"""
    db = _table(config)
    name = item if item in db else find_item(item, config)
    cat = db.get(name)
    if not cat:
        return ""
    label, why = _CATEGORY[cat]
    return f"{name}属于「{label}」。{why}"


def is_sort_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("垃圾分类", "怎么分类", "什么垃圾", "哪类垃圾", "哪种垃圾",
                            "怎么扔", "归哪类", "是干垃圾还是湿")):
        return bool(find_item(u, config)) or "垃圾分类" in u or "怎么分类" in u
    return False
