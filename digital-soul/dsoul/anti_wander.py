"""防走失：上年纪、尤其记性不好（认知症/失智）的老人,容易走丢。这一块讲两件事——
平时怎么防（信息卡、定位、告知邻里），和万一走失了立刻怎么办（别等、报警、发协查、查监控）。
家有这样的老人，提前做好，能少揪心、关键时刻能救命。纯逻辑、可单测。
和"现场迷路安抚"(lost_help)接着用：那个安抚当事人，这个帮家人防范和找人。
"""

from __future__ import annotations

# 预防 主题 -> (怎么做, 提醒)
_PREVENT = {
    "信息卡": ("给老人随身带一张'平安信息卡'：写上姓名、家人电话、家庭住址，有疾病（如高血压、认知症）也写上;"
            "放在常穿衣服口袋、挂在脖子上或缝进衣服。",
            "卡片几毛钱、关键时刻能让好心人和警察联系上你。"),
    "黄手环定位": ("戴个'黄手环'或定位手表/防走失手环——有的能一键呼叫、实时定位;"
              "或给老人手机开'实时位置共享'，家人随时看得到。",
              "定位设备记得充电、绑好家人号码、定期看好不好使。"),
    "衣物标记": ("在老人常穿的外套、裤子上缝个布条或写上家人电话和地址;"
              "走失时身上的标记就是线索。",
              "深色衣服用浅色笔，写清楚、缝牢固。"),
    "告知邻里": ("跟小区保安、门口商铺、常去的菜场和邻居打声招呼，说明老人记性不好、"
              "看见单独走远了帮忙留意、给你打电话。",
              "多一双眼睛多一分安心，远亲不如近邻。"),
    "陪伴门禁": ("失智老人单独出门风险大，尽量有人陪;门口装个开门提醒（风铃/感应器），"
              "夜里锁好门、藏好钥匙别让独自外出;固定活动范围、记牢回家的路。",
              "不是限制自由，是怕走丢——陪着遛弯，既安全又是陪伴。"),
    "留近照": ("家里存几张老人'近期、清晰'的正面照片，记下身高、特征、习惯去的地方;"
            "万一走失，立刻能用来发协查、给警察。",
            "照片每隔一阵更新一张，穿当季衣服的最有用。"),
}

# 走失后 处置步骤
_AFTER = [
    "①立刻沿常走的路线、附近公园/菜场/老房子/车站找，分头行动、保持电话畅通。",
    "②马上报警打 110——老人走失属紧急情况，不用等 24 小时，越早越好。",
    "③发协查：本地微信群、朋友圈、'头条寻人'等平台，带上近照、走失时间地点、当天穿着特征。",
    "④查监控：联系走失地附近的商铺、小区、路口、公交地铁，调监控看走向。",
    "⑤去可能的地方找：老人常念叨的旧居、子女家、熟悉的地方,以及医院、救助站、派出所问一问。",
]


def _all(config=None) -> dict:
    d = dict(_PREVENT)
    cfg = (config or {}).get("anti_wander") if isinstance(config, dict) else None
    extra = (cfg or {}).get("prevent") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("tip", "")))
    return d


def prevent_topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出预防的哪一招（名/触发，最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    alias = {
        "信息卡": "信息卡", "平安卡": "信息卡", "联系卡": "信息卡",
        "黄手环": "黄手环定位", "定位": "黄手环定位", "定位手表": "黄手环定位", "手环": "黄手环定位",
        "衣物标记": "衣物标记", "衣服标记": "衣物标记", "缝电话": "衣物标记",
        "告知邻里": "告知邻里", "邻里": "告知邻里", "邻居留意": "告知邻里",
        "陪伴门禁": "陪伴门禁", "门禁": "陪伴门禁", "有人陪": "陪伴门禁",
        "留近照": "留近照", "近照": "留近照", "照片": "留近照",
    }
    for w in sorted(alias, key=len, reverse=True):
        if w in u:
            return alias[w]
    for name in _all(config):
        if name in u:
            return name
    return None


def prevent_advice(topic, config=None) -> str:
    """某一招怎么做 + 提醒。查不到返回空。"""
    d = _all(config)
    if topic not in d:
        return ""
    how, tip = d[topic]
    return f"{topic}：{how}" + (f"（{tip}）" if tip else "")


def prevent_all(config=None) -> str:
    """防走失总清单。"""
    items = "；".join(f"{k}" for k in _all(config))
    return ("防老人走失，提前做好这几样：" + items +
            "。核心：随身带能联系上家人的信息（卡/手环）、能定位、邻里知情、留好近照。")


def what_to_do() -> str:
    """万一走失了，立刻怎么办。"""
    return "万一老人走失，别慌、立刻行动：\n" + "\n".join(_AFTER) + "\n记住：报警不用等 24 小时，越早越好。"


def is_wander_query(utterance, config=None) -> bool:
    """是不是在问防走失 / 老人走失怎么办。"""
    u = str(utterance or "")
    if any(k in u for k in ("防走失", "防走丢", "老人走失", "老人走丢", "走失了怎么办",
                            "走丢了怎么办", "黄手环", "防走失手环")):
        return True
    if ("走失" in u or "走丢" in u) and any(k in u for k in ("怎么", "咋办", "防", "找")):
        return True
    if find_topic(u, config) and any(k in u for k in ("防走失", "走失", "走丢", "老人", "怎么防")):
        return True
    return False


def wants_after(utterance) -> bool:
    """是不是已经走失了、在问怎么找（而非预防）。"""
    u = str(utterance or "")
    return ("走失了" in u or "走丢了" in u or "找不到人" in u or "不见了" in u) \
        and any(k in u for k in ("怎么办", "咋办", "怎么找", "找"))
