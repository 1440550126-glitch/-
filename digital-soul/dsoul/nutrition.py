"""膳食养生：想补钙、补血、护眼、护心该多吃点啥——用家常食物调养，吃出好身体。
（治咳嗽上火那种食疗方归 food_remedy，这儿讲日常‘吃什么补什么’。）

饮食调养、均衡为本，仅供参考，不替代医嘱。纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

# 需求 → (触发词, 多吃点啥)
_NEEDS = [
    {"name": "补钙", "keys": ["补钙", "钙", "骨质疏松", "腿抽筋", "骨头"],
     "food": "牛奶酸奶、豆腐豆浆、虾皮、芝麻酱、绿叶菜都补钙；再多晒晒太阳帮着吸收。"},
    {"name": "补血", "keys": ["补血", "贫血", "补铁", "气血", "脸色差"],
     "food": "瘦红肉、动物肝脏（适量）、红枣、菠菜、黑木耳、桂圆，配点维C的水果更好吸收。"},
    {"name": "护眼", "keys": ["护眼", "眼睛", "明目", "视力", "看东西模糊"],
     "food": "胡萝卜、菠菜、玉米、蓝莓、枸杞对眼睛好；少盯手机，多远眺。"},
    {"name": "护心", "keys": ["护心", "心脏", "血管", "心血管"],
     "food": "深海鱼、燕麦、坚果、深色蔬菜对心血管好；少油少盐、别太累、心放宽。"},
    {"name": "健脑", "keys": ["健脑", "记性", "脑子", "补脑", "老年痴呆"],
     "food": "核桃、深海鱼、鸡蛋、坚果、蓝莓有益大脑；多动脑、多走动也很重要。"},
    {"name": "润肠通便", "keys": ["便秘", "通便", "润肠", "排便", "上火便秘"],
     "food": "多吃粗粮、芹菜、红薯、香蕉、火龙果，多喝温水、多走动，肠子就通畅。"},
    {"name": "降三高", "keys": ["三高", "血压高", "血脂高", "血糖高", "降压", "降脂"],
     "food": "少油少盐少糖，多吃芹菜、苦瓜、燕麦、深海鱼、杂粮；管住嘴、迈开腿。"},
    {"name": "养胃", "keys": ["养胃", "胃不好", "胃疼", "护胃", "肠胃"],
     "food": "小米粥、山药、南瓜、面食养胃；少吃辛辣生冷、戒烟少酒，吃七分饱、细嚼慢咽。"},
    {"name": "增强免疫", "keys": ["免疫力", "抵抗力", "容易感冒", "提高免疫"],
     "food": "饮食均衡、多吃蔬果和优质蛋白（蛋奶鱼肉豆），少熬夜、勤锻炼，身子就硬朗。"},
    {"name": "补钾", "keys": ["补钾", "缺钾", "没力气抽筋"],
     "food": "香蕉、土豆、菠菜、豆类含钾多。"},
    {"name": "助眠", "keys": ["睡不好吃什么", "安神吃", "助眠食", "失眠吃什么"],
     "food": "睡前一杯温牛奶，平时吃点小米、莲子、桂圆、酸枣仁；晚饭别太饱、睡前别喝浓茶咖啡。"},
    {"name": "老人饮食", "keys": ["老人吃什么", "老年人吃什么", "老人饮食", "老人吃啥好"],
     "food": "清淡好消化、少盐少油、蛋白质要够（蛋奶鱼肉豆腐）、蔬果多样、细嚼慢咽、七八分饱。"},
]


def _all(config) -> list:
    items = list(_NEEDS)
    if isinstance(config, dict) and isinstance(config.get("nutrition"), list):
        for it in config["nutrition"]:
            if isinstance(it, dict) and it.get("name") and it.get("food"):
                it.setdefault("keys", [it["name"]])
                items = [it] + items
    return items


def needs(config=None) -> list:
    return [n["name"] for n in _all(config)]


def find_need(query, config=None):
    u = str(query or "")
    best, blen = None, 0
    for n in _all(config):
        for k in n["keys"]:
            if k in u and len(k) > blen:
                best, blen = n, len(k)
    return best


def food_for(query, config=None) -> str:
    n = find_need(query, config)
    if not n:
        return ""
    return f"{n['name']}：{n['food']}"


def is_nutrition_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    n = find_need(u, config)
    if not n:
        return False
    return any(k in u for k in ("吃什么", "吃啥", "吃点啥", "吃点什么", "怎么补", "补点啥",
                                "吃什么好", "饮食", "多吃")) or "老人吃" in u
