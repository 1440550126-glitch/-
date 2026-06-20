"""家电帮手：洗衣机怎么用、微波炉怎么热饭、空调遥控器哪个键——一步步教长辈用明白。
说明书丢了、按键看不懂、孩子不在身边，这一块顶上。纯数据 + 纯逻辑、可单测。

⚠️ 涉及燃气、电热的，安全摆第一：闻到煤气味先关阀开窗、别打火别开电器。
"""

from __future__ import annotations

# 家电 -> (怎么用, 安全/提醒)
_APPLIANCES = {
    "洗衣机": ("①衣服别塞太满，深浅色分开；②倒洗衣液到指定槽（别多倒）；③盖好盖子，"
             "选程序（一般'标准'就行，羽绒/羊毛有专门档）；④按'启动'。洗完及时晾，别捂着。",
             "进水不洗就检查水龙头开没开、门盖关严没。"),
    "微波炉": ("①饭菜放进去，盖个微波专用盖或不盖；②关好门，转时间旋钮或按数字+'启动'，"
             "热饭一两分钟先试；③'叮'一声好了，小心烫。",
             "千万别放金属、带金边的碗、鸡蛋、密封罐——会打火或爆。"),
    "电饭煲": ("①米淘好放内胆，加水（食指量：水没过米后再高出一指节）；②内胆擦干外壁放进去、盖好；"
             "③插电，按'煮饭'，跳到'保温'就熟了，焖几分钟更香。",
             "内胆外面和发热盘要干净干燥再放进去。"),
    "空调遥控器": ("①按'开关'开机；②'模式'键切换：雪花=制冷、太阳=制热、水滴=除湿；"
                "③'温度'上下键调度数（夏天 26 度最舒服）；④'风速'调大小，'扫风'让风左右上下摆。",
                "制冷别贪低，26 度护着身子；长时间开记得通通风。"),
    "电视机顶盒": ("①电视和机顶盒都要开（两个遥控器）；②电视遥控按'信号源'/'TV/AV'，"
                "切到 HDMI 那一路才有画面；③之后用机顶盒遥控换台、调音量。",
                "没画面多半是'信号源'没切对，挨个 HDMI 试一遍。"),
    "燃气灶": ("①先开燃气总阀；②按下灶具旋钮并转到'点火'，听到'啪'打着火、出蓝火苗；"
             "③调火大小，做完把旋钮关到底、再关总阀。",
             "打不着别连续猛按；闻到煤气味：别开火别开灯，先关阀、开窗、出门打电话。"),
    "热水器": ("①电热的：插电、等水烧热（看指示灯/温度），用时混冷水调温；"
             "②燃气的：开燃气阀和水阀，一开热水龙头就自动点火出热水。",
             "电热水器洗澡时最好断电再洗更稳妥；燃气的保持通风别闷罐。"),
    "电磁炉": ("①坐上专用的铁锅（玻璃、砂锅不行）；②插电、开机，选'炒菜/煮汤/火锅'或直接调火力；"
             "③用完关机拔电，炉面还烫别马上摸。",
             "只认铁锅/钢锅；炉面别放金属勺、银行卡、手机。"),
    "电压力锅": ("①食材加水放内胆，盖盖子转到锁紧位置（对准标记）；②选'煮饭/炖肉/煮粥'，"
               "③等它自己泄压、浮子落下去才能开盖。",
               "没泄压完别硬开盖！可拨'排气'放完气再开。"),
}

_ALIAS = {
    "洗衣机": "洗衣机", "洗衣服机器": "洗衣机", "甩干": "洗衣机",
    "微波炉": "微波炉", "热饭": "微波炉", "微波": "微波炉",
    "电饭煲": "电饭煲", "电饭锅": "电饭煲", "煮饭锅": "电饭煲",
    "空调遥控": "空调遥控器", "空调遥控器": "空调遥控器", "空调怎么": "空调遥控器", "空调遥控板": "空调遥控器",
    "机顶盒": "电视机顶盒", "电视怎么": "电视机顶盒", "电视没画面": "电视机顶盒", "电视没图像": "电视机顶盒",
    "信号源": "电视机顶盒",
    "燃气灶": "燃气灶", "煤气灶": "燃气灶", "灶台": "燃气灶", "打不着火": "燃气灶", "天然气灶": "燃气灶",
    "热水器": "热水器",
    "电磁炉": "电磁炉",
    "电压力锅": "电压力锅", "高压锅": "电压力锅", "压力锅": "电压力锅",
}


def _all(config=None) -> dict:
    d = dict(_APPLIANCES)
    cfg = (config or {}).get("appliances") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("steps"):
                d[str(name)] = (str(v["steps"]), str(v.get("tip", "")))
    return d


def appliances(config=None) -> list:
    return list(_all(config).keys())


def find_appliance(utterance, config=None):
    """认出问的哪个家电（名/别名，最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def how_to(name, config=None) -> str:
    """某家电怎么用（步骤 + 安全提醒）。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(name or ""), str(name or ""))
    if key not in d:
        return ""
    steps, tip = d[key]
    return f"{key}怎么用：{steps}" + (f"（安全：{tip}）" if tip else "")


def is_appliance_query(utterance, config=None) -> bool:
    """是不是在问家电怎么用（认出家电 + 怎么用/不会/打不着 的意图）。"""
    u = str(utterance or "")
    if not find_appliance(u, config):
        return False
    if any(k in u for k in ("不会用", "不会弄", "教教", "教我", "打不着", "不出", "没画面",
                            "没图像", "用法")):
        return True
    # 泛问"怎么/咋"也算，但排除明显的报故障（那是要修，不是问用法）
    if ("怎么" in u or "咋" in u) and not any(b in u for b in ("坏", "故障", "报修", "响",
                                                              "费电", "噪音", "漏水", "不转", "罢工")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
