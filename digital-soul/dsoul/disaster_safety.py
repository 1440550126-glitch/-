"""灾害自救：地震、台风、洪水、打雷、火场逃生、中暑、溺水——关键时刻怎么保命。
（用电燃气那种居家安全归 home_safety，这儿讲突发灾害。）平时记一记，真遇上不慌。

纯逻辑、可单测。常识性自救要点，紧急情况以官方指引和 120/119 为准。
"""

from __future__ import annotations

_SCENARIOS = [
    {"name": "地震", "keys": ["地震", "地动", "震感"],
     "tip": "在室内：就近躲到结实的桌子下、承重墙墙角，护住头颈，远离窗户和吊灯；"
            "别坐电梯、别跳楼。摇晃停了再有序往空旷处撤。在室外就跑到开阔地，避开高楼、电线。"},
    {"name": "台风", "keys": ["台风", "刮大风", "强风"],
     "tip": "关好门窗、加固阳台杂物，尽量别出门；非出不可就远离广告牌、大树、临时搭建物；"
            "提前备点食物、水和手电，留意官方预警。"},
    {"name": "洪水", "keys": ["洪水", "发大水", "涨水", "内涝"],
     "tip": "往高处转移，别趟不明深浅的水流（井盖可能被冲开）；抓住门板、桶等能浮的东西；"
            "断电断气，备好饮用水，听从转移安排。"},
    {"name": "雷电", "keys": ["打雷", "雷电", "闪电", "雷暴"],
     "tip": "别在大树下、电线杆旁、空旷高处避雨，别打手机、别碰金属；"
            "尽快进屋，进屋后拔掉电器插头、关好门窗、别用太阳能热水器洗澡。"},
    {"name": "火场逃生", "keys": ["着火", "失火", "起火", "火灾逃生", "房子着火", "楼里着火"],
     "tip": "用湿毛巾捂住口鼻、压低身子贴墙走；走楼梯别坐电梯；"
            "开门前先摸门把，烫就别开、换路线或退回房间塞住门缝、到窗口呼救；逃出后别再返回。"},
    {"name": "中暑", "keys": ["中暑", "热晕", "暑热"],
     "tip": "赶紧到阴凉通风处，松开衣服、扇风降温、喝点淡盐水；"
            "用湿毛巾敷额头脖子。要是高烧、神志不清，立刻打 120。"},
    {"name": "溺水救援", "keys": ["有人溺水", "落水", "溺水了", "掉水里"],
     "tip": "不会水千万别贸然下水、也别手拉手去拉——容易被一起拖下去；"
            "递长杆、抛绳子或漂浮物，大声呼救、打 120。救上岸后清理口鼻、必要时做心肺复苏。"},
    {"name": "煤气泄漏应急", "keys": ["煤气漏了", "燃气泄漏怎么办", "闻到煤气"],
     "tip": "千万别开关任何电器、别打火、别按门铃——先关总阀、开窗通风，人到屋外再打电话报修。"},
]


def _all(config) -> list:
    items = list(_SCENARIOS)
    if isinstance(config, dict) and isinstance(config.get("disaster_safety"), list):
        for it in config["disaster_safety"]:
            if isinstance(it, dict) and it.get("name") and it.get("tip"):
                it.setdefault("keys", [it["name"]])
                items = [it] + items
    return items


def scenarios(config=None) -> list:
    return [s["name"] for s in _all(config)]


def find_scenario(query, config=None):
    u = str(query or "")
    best, blen = None, 0
    for s in _all(config):
        for k in s["keys"]:
            if k in u and len(k) > blen:
                best, blen = s, len(k)
    return best


def tip_for(query, config=None) -> str:
    s = find_scenario(query, config)
    return f"{s['name']}自救：{s['tip']}" if s else ""


def is_disaster_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if "自救" in u or "逃生" in u:
        return bool(find_scenario(u, config)) or "自救" in u
    if find_scenario(u, config) and any(k in u for k in ("怎么办", "咋办", "怎么躲", "注意",
                                                         "怎么跑", "如何", "怎么逃", "来了")):
        return True
    return False
