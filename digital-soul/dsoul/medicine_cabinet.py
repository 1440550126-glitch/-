"""家庭小药箱：家里该常备点啥——退烧的、止泻的、消毒的、慢病要紧的，一样样备齐，
真有个头疼脑热、磕了碰了，不至于半夜抓瞎。按用途分门别类，再提醒看保质期、放对地方。

⚠️ 这只是"该备哪些"的清单，具体怎么吃、吃多少，看说明书或遵医嘱；
慢病的药（降压降糖等）更要听医生的，别擅自停、换、加量。
纯数据 + 纯逻辑、可单测。可在 config 的 medicine_cabinet 里按自家情况增减。
"""

from __future__ import annotations

# 用途 -> ([该备的东西], 一句提醒)
_CABINET = {
    "退烧止痛": (
        ["对乙酰氨基酚（退烧/头疼）", "布洛芬（退烧/关节肌肉痛）"],
        "两种别叠着吃；肝肾不好、在吃别的药，先问医生。"),
    "感冒": (
        ["对症感冒药（流涕/鼻塞/咳嗽各有侧重，按症状选）", "润喉含片", "板蓝根等清热中成药"],
        "感冒药别和退烧药成分撞车（很多含对乙酰氨基酚），看清成分。"),
    "肠胃": (
        ["蒙脱石散（止泻）", "口服补液盐（拉肚子补水防脱水）", "健胃消食片", "开塞露（便秘应急）", "抗酸药（烧心反酸）"],
        "拉肚子最怕脱水，补液盐比白水管用；老人小孩腹泻别硬扛，重了就医。"),
    "外伤消毒": (
        ["碘伏（消毒，不像酒精那么疼）", "创可贴（大小几种）", "医用棉签/棉球", "无菌纱布 + 医用胶带", "医用酒精（擦物体/器械）"],
        "伤口消毒用碘伏更温和；酒精别直接倒在大伤口上。"),
    "过敏止痒": (
        ["氯雷他定/西替利嗪（抗过敏，不太犯困）", "炉甘石洗剂（蚊虫叮咬、湿疹止痒）"],
        "突发严重过敏（喉头发紧、呼吸困难）别等药，直接打120。"),
    "烫伤": (
        ["烫伤膏（如湿润烧伤膏）", "无菌纱布"],
        "先凉水冲再涂；起大泡、面积大别自己处理，去医院。"),
    "慢病常备": (
        ["降压药（按医嘱备足，别断）", "降糖药/胰岛素", "速效救心丸/硝酸甘油（冠心病随身带）", "雾化/平喘药（哮喘老慢支）"],
        "这些因人而异、必须遵医嘱；快吃完提前续上，千万别断顿。"),
    "工具器材": (
        ["体温计（电子的好读）", "血压计（家用电子臂式）", "血糖仪 + 试纸（糖尿病）", "口罩", "医用手套", "小镊子", "用药记录本"],
        "血压血糖记下来给医生看最有用；体温计血压计定期校准。"),
}

_ALIAS = {
    "退烧止痛": "退烧止痛", "退烧": "退烧止痛", "退热": "退烧止痛", "止痛": "退烧止痛", "头疼药": "退烧止痛",
    "感冒": "感冒", "感冒药": "感冒", "伤风": "感冒", "鼻塞": "感冒",
    "肠胃": "肠胃", "拉肚子": "肠胃", "腹泻": "肠胃", "便秘": "肠胃", "消化": "肠胃", "胃药": "肠胃",
    "外伤消毒": "外伤消毒", "消毒": "外伤消毒", "创可贴": "外伤消毒", "碘伏": "外伤消毒", "包扎": "外伤消毒", "外伤": "外伤消毒",
    "过敏止痒": "过敏止痒", "过敏": "过敏止痒", "止痒": "过敏止痒", "蚊虫": "过敏止痒",
    "烫伤": "烫伤", "烧伤": "烫伤",
    "慢病常备": "慢病常备", "慢病": "慢病常备", "降压药": "慢病常备", "降糖": "慢病常备", "救心丸": "慢病常备",
    "工具器材": "工具器材", "工具": "工具器材", "体温计": "工具器材", "血压计": "工具器材", "器材": "工具器材",
}


def _all(config=None) -> dict:
    d = {k: (list(v[0]), v[1]) for k, v in _CABINET.items()}
    cfg = (config or {}).get("medicine_cabinet") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for cat, v in extra.items():
            if isinstance(v, (list, tuple)) and v and isinstance(v[0], list):
                d[str(cat)] = (list(v[0]), str(v[1]) if len(v) > 1 else "")
            elif isinstance(v, list):
                d[str(cat)] = (list(v), "")
            elif isinstance(v, dict) and v.get("items"):
                d[str(cat)] = (list(v["items"]), str(v.get("tip", "")))
    return d


def categories(config=None) -> list:
    return list(_all(config).keys())


def find_category(utterance, config=None):
    """听出问的哪类（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for cat in _all(config):
        if cat in u:
            return cat
    return None


def items_for(category, config=None) -> list:
    cat = _ALIAS.get(str(category or ""), str(category or ""))
    pair = _all(config).get(cat)
    return list(pair[0]) if pair else []


def advise(category, config=None) -> str:
    """某一类该备啥 + 提醒。查不到返回空。"""
    cat = _ALIAS.get(str(category or ""), str(category or ""))
    pair = _all(config).get(cat)
    if not pair:
        return ""
    items, tip = pair
    return f"【{cat}】该备：" + "、".join(items) + "。" + (f"（{tip}）" if tip else "")


def checklist(config=None) -> str:
    """一份完整的小药箱清单（分类列出）。"""
    lines = [f"·{cat}：" + "、".join(items) for cat, (items, _t) in _all(config).items()]
    head = "家庭小药箱备这些，分门别类放好：\n"
    return head + "\n".join(lines) + "\n（用法用量遵说明书/医嘱；慢病药别擅自停换，定期看保质期。）"


def tips() -> list:
    """管理小药箱的几条。"""
    return [
        "定期清一次，过期、受潮、变色的别留，及时换新。",
        "内服外用分开放，标签朝外，名字看得清。",
        "放在阴凉干燥处，孩子够不到的地方。",
        "慢病的药别等吃完才想起，提前续上，绝不断顿。",
        "记下家人过敏的药，本子或药箱盖上写一张。",
    ]


def count(config=None) -> int:
    return sum(len(items) for items, _t in _all(config).values())


def is_cabinet_query(utterance, config=None) -> bool:
    """是不是在问家里该备什么药/小药箱。"""
    u = str(utterance or "")
    if any(k in u for k in ("小药箱", "常备药", "家里备什么药", "备点什么药", "该备什么药",
                            "药箱", "家庭备药", "备药清单")):
        return True
    # "拉肚子/感冒 该备什么药" + 备/常备/家里
    if find_category(u, config) and any(k in u for k in ("备什么", "备点", "备啥", "常备", "家里备", "该备", "备哪些")):
        return True
    return False
