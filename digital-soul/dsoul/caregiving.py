"""照护卧床老人：长期卧床、大病初愈在床上的老人，怎么照顾才少受罪、少出并发症——
防褥疮、喂饭防呛、清洁、防肺炎、帮着活动、还有心理陪伴。照护者自己也得歇着点。
纯逻辑、可单测。

⚠️ 这是居家照护常识，具体听医生护士的指导；情况复杂、有伤口/发烧/呛咳等及时就医。
"""

from __future__ import annotations

# 主题 -> (怎么做, 提醒)
_TOPICS = {
    "防褥疮": ("勤翻身——大约每 2 小时翻一次身、换换姿势;骨头突出的地方（屁股、脚跟、肩胛）垫软枕分散压力;"
            "保持皮肤干爽干净、床单平整没皱褶;有条件用气垫床。",
            "皮肤发红、破皮是褥疮前兆，发红处别去揉按、赶紧减压并告诉医护。"),
    "喂饭防呛": ("先把人扶起来坐着或半卧（别躺着喂）;一小口一小口慢慢喂、咽下去再喂下一口;"
              "食物弄稠一点（太稀的水反而易呛）;喂完别马上躺下，坐一会儿。",
              "一旦呛咳厉害、喘不上气，立刻停、让身体前倾拍背，严重打 120。"),
    "口腔清洁": ("每天给老人清洁口腔（漱口或用棉签蘸水擦），不能进食的也要做;假牙取下泡好。",
             "口腔脏容易引起感染和吸入性肺炎，这步别省。"),
    "大小便护理": ("勤换尿垫尿不湿、便后温水擦洗会阴并擦干，防红屁股和感染;留意尿量、有没有便秘或腹泻。",
                "几天不排便、尿少尿痛、皮肤破溃，告诉医生。"),
    "防肺炎": ("长期躺着痰排不出易得'坠积性肺炎'：多翻身、空心掌从下往上拍拍背帮排痰;"
            "能摇高床头就半坐着;屋里常通风、别太干。",
            "发烧、咳脓痰、呼吸快，赶紧就医。"),
    "活动关节": ("每天帮老人轻轻活动手脚的关节（屈伸、转动），防止关节僵硬、肌肉萎缩;动作轻柔、别硬掰。",
             "能动的鼓励自己动一动，哪怕一点点。"),
    "心理陪伴": ("多陪着说说话、放放老歌老戏、开窗让看看外头;别在老人面前唉声叹气、别让他觉得自己是累赘;"
              "保留他的体面和做主的小事。",
              "人躺着，心更需要暖着。你的陪伴比什么都管用。"),
    "照护者歇口气": ("照顾人是真累、真熬人。你也得吃好睡好、轮换着来、该求助就求助（亲戚、护工、社区喘息服务）;"
                "别一个人硬扛到自己垮掉。",
                "把自己照顾好，才照顾得动他——这不是自私，是必须。"),
}

_ALIAS = {
    "防褥疮": "防褥疮", "褥疮": "防褥疮", "压疮": "防褥疮", "翻身": "防褥疮", "生褥疮": "防褥疮",
    "喂饭防呛": "喂饭防呛", "喂饭": "喂饭防呛", "喂饭呛": "喂饭防呛", "呛": "喂饭防呛", "怎么喂": "喂饭防呛",
    "口腔清洁": "口腔清洁", "口腔护理": "口腔清洁", "清洁口腔": "口腔清洁",
    "大小便护理": "大小便护理", "大小便": "大小便护理", "换尿垫": "大小便护理", "尿不湿": "大小便护理", "红屁股": "大小便护理",
    "防肺炎": "防肺炎", "坠积性肺炎": "防肺炎", "拍背": "防肺炎", "排痰": "防肺炎",
    "活动关节": "活动关节", "关节僵硬": "活动关节", "肌肉萎缩": "活动关节", "活动手脚": "活动关节",
    "心理陪伴": "心理陪伴", "陪伴": "心理陪伴", "心理": "心理陪伴",
    "照护者歇口气": "照护者歇口气", "照护者": "照护者歇口气", "照顾人累": "照护者歇口气", "护工": "照护者歇口气",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("caregiving") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("tip", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问照护的哪一块（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    if "照顾" in u and any(k in u for k in ("太累", "好累", "扛不住", "撑不住", "累垮", "受不了")):
        return "照护者歇口气"      # 照护者吐露太累，给那句"你也得歇"
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某块照护怎么做 + 提醒 + 免责。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    how, tip = d[key]
    return f"{key}：{how}" + (f"（{tip}）" if tip else "") + "（居家照护常识，具体听医护指导。）"


def overview() -> str:
    """照护卧床老人的几件要紧事。"""
    return ("照护卧床的老人，盯紧这几样：勤翻身防褥疮、坐起来慢喂防呛、做好口腔和大小便清洁、"
            "多翻身拍背防肺炎、帮着活动关节、多陪着说说话。还有一条——照护者自己也要歇、要求助，"
            "别硬扛垮了。具体听医生护士的。")


def is_caregiving_query(utterance, config=None) -> bool:
    """是不是在问照护卧床老人。"""
    u = str(utterance or "")
    if any(k in u for k in ("卧床", "照护", "陪护", "照顾老人", "怎么护理", "护理老人")):
        return True
    # 照护者吐露太累/扛不住——给他那句"你也得歇"
    if "照顾" in u and any(k in u for k in ("太累", "好累", "扛不住", "撑不住", "累垮", "受不了")):
        return True
    if find_topic(u, config) and any(k in u for k in ("怎么", "咋", "护理", "怎么办", "注意", "防")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
