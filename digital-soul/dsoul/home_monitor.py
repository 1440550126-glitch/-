"""居家监测：血压怎么量才准、血糖啥时候测、体温量哪儿、脉搏怎么数——在家自己测对了，
心里才有底，给医生看也准。和"体检解读"(checkup 看懂数值)、"小药箱"(measure 工具)接着用。
纯逻辑、可单测。

⚠️ 自测是为了心里有数，不替代看病；数值不对劲、人不舒服，及时就医。
"""

from __future__ import annotations

# 监测项 -> (怎么做对, 正常参考, 提醒)
_ITEMS = {
    "量血压": ("先静坐 5 分钟、别憋尿；坐正、后背靠好、脚平放别翘腿；袖带绑上臂、和心脏一个高度；"
             "量的时候别说话别动；最好早晚各量一次、每次量 1～2 遍取稳定值。",
             "理想约 120/80；高压持续≥140 或低压≥90 就算偏高。",
             "把数值记下来给医生看；别只量一次就紧张，多记几天更准。"),
    "测血糖": ("空腹测要隔夜禁食 8 小时以上、早起没吃饭时测；餐后血糖从吃第一口饭算起 2 小时测；"
             "扎指尖侧面（不那么疼）、酒精消毒等干了再扎；第一滴血擦掉、用第二滴。",
             "空腹约 3.9～6.1；餐后 2 小时一般 <7.8。",
             "试纸别过期、对好码；低血糖（心慌手抖出汗）赶紧吃块糖。"),
    "量体温": ("腋下擦干、夹紧水银温度计 5 分钟读数；电子额温枪对准额头、耳温枪塞耳道；"
             "刚运动、刚喝热水、刚洗澡先缓 20 分钟再量。",
             "正常约 36～37℃；腋温超过 37.3℃ 算发热。",
             "水银表用前甩到 35 度以下；摔碎了别用手碰水银、开窗通风。"),
    "数脉搏": ("安静坐着，用食指中指按住手腕大拇指那一侧的动脉，数 15 秒的次数再乘以 4，"
             "就是一分钟心跳；或直接看电子血压计上的心率。",
             "成人安静时约 60～100 次/分。",
             "跳得忽快忽慢、心慌明显，记下来告诉医生。"),
    "称体重": ("晨起、空腹、排空大小便后，穿差不多的衣服、用同一台秤、放平地上称，最准、好对比。",
             "胖瘦看 BMI：体重(kg)÷身高(m)的平方，18.5～23.9 算正常。",
             "每周固定一天称一次就够，别天天上秤较真。"),
}

_ALIAS = {
    "量血压": "量血压", "测血压": "量血压", "血压怎么量": "量血压", "血压计怎么用": "量血压", "量血压准": "量血压",
    "测血糖": "测血糖", "量血糖": "测血糖", "血糖怎么测": "测血糖", "扎手指": "测血糖", "血糖仪": "测血糖",
    "量体温": "量体温", "测体温": "量体温", "量温度": "量体温", "体温怎么量": "量体温",
    "额温枪": "量体温", "体温": "量体温",
    "数脉搏": "数脉搏", "量脉搏": "数脉搏", "数心跳": "数脉搏", "量心率": "数脉搏", "测心率": "数脉搏",
    "称体重": "称体重", "量体重": "称体重", "称重": "称体重",
}


def _all(config=None) -> dict:
    d = dict(_ITEMS)
    cfg = (config or {}).get("home_monitor") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 3:
                d[str(name)] = (str(v[0]), str(v[1]), str(v[2]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("normal", "")), str(v.get("tip", "")))
    return d


def items(config=None) -> list:
    return list(_all(config).keys())


def find_item(utterance, config=None):
    """认出测哪项（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def how_to(item, config=None) -> str:
    """某项怎么测对（步骤 + 正常参考 + 提醒 + 免责）。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(item or ""), str(item or ""))
    if key not in d:
        return ""
    how, normal, tip = d[key]
    body = f"{key}：{how}"
    if normal:
        body += f" 正常参考：{normal}"
    if tip:
        body += f"（{tip}）"
    return body + "（自测心里有数就好，不替代看病；不对劲及时就医。）"


def is_monitor_query(utterance, config=None) -> bool:
    """是不是在问怎么自测（认出项目 + 怎么量/怎么测/准不准 的意图）。"""
    u = str(utterance or "")
    if not find_item(u, config):
        return False
    return any(k in u for k in ("怎么量", "怎么测", "怎么数", "怎么称", "咋量", "咋测", "准不准",
                                "量准", "测准", "什么时候", "啥时候", "正常", "多少正常", "怎么用",
                                "教教", "教我", "对不对", "量哪", "测哪", "量哪儿", "哪儿"))


def count(config=None) -> int:
    return len(_all(config))
