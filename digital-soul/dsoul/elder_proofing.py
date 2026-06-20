"""居家适老改造：家里按"防摔、好用、安全"改一改，老人住得稳当、家人少操心。
老人最怕摔，一摔可能就卧床——一点点改造，能挡掉好多意外。按房间一处处说。
纯逻辑、可单测。和"居家安全常识"(home_safety)接着用，这里讲"怎么改造"。
"""

from __future__ import annotations

# 区域 -> (怎么改, 重点提醒)
_AREAS = {
    "卫生间": ("最易滑倒的地方：马桶旁、淋浴区装'扶手';地面铺'防滑垫';淋浴备个'防滑洗澡凳'坐着洗;"
            "用坐便器更省力;热水器调好温度防烫;夜里留盏灯。",
            "卫生间地滑 + 起身猛，是摔跤高发地，这几样最该改。"),
    "卧室": ("床高到坐下脚能踏实着地、好起身;床边可装扶手、放个小夜灯（夜里起夜照路）;"
           "常用的水杯、药、眼镜、手机放在伸手够得着的床头。",
           "起夜摔倒最多——小夜灯 + 床边扶手很管用。"),
    "客厅过道": ("去掉门槛、卷边的小地毯（最绊脚）;走道留宽、别堆杂物;电线沿墙收好别横在地上;"
              "沙发别太矮太软（陷进去难起身）;过道装感应夜灯。",
              "地上'别有绊脚的、别打滑的、别堆东西'，这是防摔铁律。"),
    "厨房": ("常用的锅碗调料放在不弯腰不踮脚的顺手高度;地上铺防滑垫、随手擦干水渍;"
           "装个燃气报警器;煮东西人别离开看着火。",
           "别让老人爬高拿东西，常用的都放在手边高度。"),
    "楼梯门口": ("楼梯两侧都装扶手、台阶贴防滑条、照明要足、踏面别太窄;门口放个换鞋凳坐着换鞋;"
              "进门处装灯、钥匙挂固定位置。",
              "上下楼扶稳、看清，别端着东西挡视线。"),
    "通用": ("穿防滑的鞋/拖鞋;家具尖角包上防撞条;各屋夜里都有微光;装个紧急呼叫或手机一键拨号;"
           "地面始终保持干、平、净。",
           "再加一条：常和家人保持联系，独居更要装个能呼救的。"),
}

_ALIAS = {
    "卫生间": "卫生间", "厕所": "卫生间", "洗手间": "卫生间", "浴室": "卫生间", "淋浴": "卫生间", "马桶": "卫生间",
    "卧室": "卧室", "床": "卧室", "起夜": "卧室", "睡房": "卧室",
    "客厅过道": "客厅过道", "客厅": "客厅过道", "过道": "客厅过道", "走廊": "客厅过道", "地毯": "客厅过道", "门槛": "客厅过道",
    "厨房": "厨房", "灶台": "厨房",
    "楼梯门口": "楼梯门口", "楼梯": "楼梯门口", "台阶": "楼梯门口", "门口": "楼梯门口",
    "通用": "通用", "整体": "通用", "全屋": "通用",
}


def _all(config=None) -> dict:
    d = dict(_AREAS)
    cfg = (config or {}).get("elder_proofing") if isinstance(config, dict) else None
    extra = (cfg or {}).get("areas") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("tip", "")))
    return d


def areas(config=None) -> list:
    return list(_all(config).keys())


def find_area(utterance, config=None):
    """认出问哪个区域（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def suggest(area, config=None) -> str:
    """某区域怎么改 + 提醒。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(area or ""), str(area or ""))
    if key not in d:
        return ""
    how, tip = d[key]
    return f"{key}：{how}" + (f"（{tip}）" if tip else "")


def checklist(config=None) -> str:
    """一份适老改造总清单（各区域要点）。"""
    lines = [f"·{a}：{how}" for a, (how, _t) in _all(config).items()]
    return "居家适老改造，按房间过一遍：\n" + "\n".join(lines) + "\n核心就三条：防摔、好够着、能呼救。"


def is_proofing_query(utterance, config=None) -> bool:
    """是不是在问居家适老改造/防摔布置。"""
    u = str(utterance or "")
    if any(k in u for k in ("适老", "适老化", "适老改造", "防摔改造", "老人房间怎么", "防跌倒改造")):
        return True
    if find_area(u, config) and any(k in u for k in ("适老", "改造", "防摔", "防滑", "怎么布置",
                                                     "装扶手", "老人怎么", "怎么改", "防跌")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
