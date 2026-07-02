"""居家安全常识：用电、燃气、防火、防滑防摔、防一氧化碳、独居老人该注意啥。
平时多留个心，少出事。（睡前过一遍门锁燃气那种清单归 safety_check，这儿讲常识。）

纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_SAFETY = [
    {"name": "用电安全", "keys": ["用电", "电器", "插座", "触电", "漏电", "电线"],
     "tip": "别用湿手插拔插座；一个插排别插太多大功率电器；人走电器断电；"
            "电线老化、插头发烫要及时换；不私拉乱接电线。"},
    {"name": "燃气安全", "keys": ["燃气", "煤气", "天然气", "瓶装气", "灶"],
     "tip": "用完随手关阀门；闻到臭鸡蛋味（漏气）别开灯、别打火、别接电话，先开窗通风、关阀、到屋外打电话；"
            "软管两三年一换，定期查。"},
    {"name": "防火", "keys": ["防火", "着火", "火灾", "失火", "灭火"],
     "tip": "别躺床上吸烟；油锅起火盖锅盖闷灭、千万别浇水；电动车别推屋里、楼道充电；"
            "易燃物远离火源；家里备个小灭火器。"},
    {"name": "防滑防摔", "keys": ["防滑", "防摔", "摔倒", "滑倒", "浴室滑", "防跌"],
     "tip": "浴室铺防滑垫、装扶手；地上的水随手擦干；起夜开盏小灯；穿防滑的鞋；"
            "别站凳子够高处，让年轻人来。"},
    {"name": "防烫", "keys": ["防烫", "烫伤", "热水", "开水"],
     "tip": "热水瓶、汤锅放稳，锅把手朝里；给孩子洗澡先放凉水再兑热水、先试温；端热汤走稳点。"},
    {"name": "防一氧化碳", "keys": ["一氧化碳", "煤气中毒", "烧炭", "中毒", "热水器"],
     "tip": "燃气热水器别装在浴室里，要通风；屋里烧炭取暖一定留通风口；"
            "闷在车里别开着空调睡觉。头晕恶心赶紧开窗到通风处、打120。"},
    {"name": "独居安全", "keys": ["独居", "一个人住", "老人独自", "独自在家"],
     "tip": "家人电话和120写大字贴墙上；手机随身带、设个紧急联系人；和家人约好每天报个平安；"
            "装个紧急呼叫器或智能音箱更稳妥。"},
    {"name": "防盗", "keys": ["防盗", "小偷", "入室", "门窗安全"],
     "tip": "出门锁好门窗；贵重东西、现金别露在外头；陌生人敲门先看清、别随便开；"
            "‘查水电’的先打物业电话核实。"},
]


def _all(config) -> list:
    items = list(_SAFETY)
    if isinstance(config, dict) and isinstance(config.get("home_safety"), list):
        for it in config["home_safety"]:
            if isinstance(it, dict) and it.get("name") and it.get("tip"):
                it.setdefault("keys", [it["name"]])
                items = [it] + items
    return items


def categories(config=None) -> list:
    return [s["name"] for s in _all(config)]


def find_topic(query, config=None):
    u = str(query or "")
    best, blen = None, 0
    for s in _all(config):
        for k in s["keys"]:
            if k in u and len(k) > blen:
                best, blen = s, len(k)
    return best


def tip_for(query, config=None) -> str:
    s = find_topic(query, config)
    return f"{s['name']}：{s['tip']}" if s else ""


def is_safety_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if "居家安全" in u or "安全常识" in u:
        return True
    if find_topic(u, config) and any(k in u for k in ("注意", "安全", "怎么防", "防范",
                                                      "小心", "要点", "讲究", "注意啥",
                                                      "怎么避免", "常识")):
        return True
    return False
