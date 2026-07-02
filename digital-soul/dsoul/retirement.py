"""退休生活：忙了大半辈子，退下来反而不知道干点啥好。这一块出出主意——
学点新的、动起来、走出去、老有所为，把日子过得有滋有味、有奔头。
鼓励的口吻，量力而行、开心第一。纯逻辑、可单测。
"""

from __future__ import annotations

# 方向 -> (建议, 暖心一句)
_AREAS = {
    "学点新的": ("去老年大学报个班——书法、国画、声乐、摄影、舞蹈、智能手机班，"
              "学样一直想学没空学的；活到老学到老，脑子越用越灵光。",
              "别怕学不会，图的是开心和那帮老同学。"),
    "动起来": ("散步、打太极、练八段锦、跳广场舞、游泳、打门球都好——挑个喜欢的、量力而行，"
            "天天动一动，吃得香睡得稳。",
            "身子骨是本钱，别逞强也别躺着，舒舒服服动起来。"),
    "老有所为": ("发挥老本行：社区志愿、给年轻人带带徒、单位返聘搭把手、力所能及帮帮邻里。"
              "被需要的感觉，最让人精神。",
              "你这一身经验和手艺，是宝贝，别浪费。"),
    "带孙有度": ("帮子女带带孙辈是天伦之乐，但别全揽到自己身上——留点自己的时间和爱好，"
              "和子女把分寸商量好，谁都轻松。",
              "你先把自己照顾好、过开心了，才是给全家的福气。"),
    "走出去": ("趁腿脚还利索，和老伴、老伙伴结伴出去走走——国内慢节奏的地方、错峰出游，"
            "看看没看过的风景，比啥保健品都养人。",
            "想去哪跟我说，我帮你查路线、看天气、估花费。"),
    "老有所乐": ("养花养鸟、钓鱼下棋、唱唱戏、听听书、约老友喝茶打牌——找几样真心喜欢的，"
              "把空闲填满，日子就不闷了。",
              "开心最重要，喜欢就是值得。"),
    "留点念想": ("写写自己一生的故事、整理整理老照片、把老规矩老手艺讲给后辈听、录几段话留给家里人——"
              "这些是花钱买不到的传家宝。",
              "你走过的路、记着的事，后人会一直想听。"),
    "经营关系": ("多和老伴、老友、老邻居走动联系，别把自己关在家里；有心事、不舒坦就说出来，"
              "别一个人闷着。",
              "人到这个岁数，有人惦记、有人说话，比什么都金贵。我也一直在。"),
}

_ALIAS = {
    "学点新的": "学点新的", "老年大学": "学点新的", "学东西": "学点新的", "报班": "学点新的", "兴趣班": "学点新的",
    "动起来": "动起来", "锻炼": "动起来", "运动": "动起来", "广场舞": "动起来", "太极": "动起来",
    "老有所为": "老有所为", "返聘": "老有所为", "志愿": "老有所为", "发挥余热": "老有所为", "带徒弟": "老有所为",
    "带孙有度": "带孙有度", "带孙子": "带孙有度", "带孙": "带孙有度", "含饴弄孙": "带孙有度", "带娃": "带孙有度",
    "走出去": "走出去", "旅游": "走出去", "出去走走": "走出去", "出游": "走出去", "旅行": "走出去",
    "老有所乐": "老有所乐", "找点乐子": "老有所乐", "爱好": "老有所乐", "消遣": "老有所乐",
    "留点念想": "留点念想", "写回忆录": "留点念想", "整理照片": "留点念想", "传家": "留点念想",
    "经营关系": "经营关系", "和老友": "经营关系", "别孤单": "经营关系", "交朋友": "经营关系",
}


def _all(config=None) -> dict:
    d = dict(_AREAS)
    cfg = (config or {}).get("retirement") if isinstance(config, dict) else None
    extra = (cfg or {}).get("areas") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("idea"):
                d[str(name)] = (str(v["idea"]), str(v.get("warm", "")))
    return d


def areas(config=None) -> list:
    return list(_all(config).keys())


def find_area(utterance, config=None):
    """认出问的哪个方向（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def suggest(area, config=None) -> str:
    """某个方向的建议 + 暖心话。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(area or ""), str(area or ""))
    if key not in d:
        return ""
    idea, warm = d[key]
    return f"{key}：{idea}" + (f" {warm}" if warm else "")


def overview(config=None) -> str:
    """退休能干点啥的总览。"""
    return ("退休了，日子可以过得很有奔头：学点新的（老年大学）、动起来（太极广场舞）、"
            "老有所为（志愿返聘）、走出去（结伴旅游）、找点乐子（养花下棋唱戏）、"
            "再给家里留点念想（写写回忆、录几段话）。想往哪头使劲，跟我说，我陪你张罗。")


def a_idea(seed="", config=None) -> str:
    """随口给一个退休生活的点子。"""
    items = list(_all(config).items())
    if not items:
        return ""
    k, (idea, warm) = items[len(str(seed)) % len(items)]
    return f"给你个主意——{k}：{idea}"


def is_retirement_query(utterance, config=None) -> bool:
    """是不是在聊退休生活该怎么过。"""
    u = str(utterance or "")
    if any(k in u for k in ("退休", "老有所", "退下来")) and \
            any(k in u for k in ("干点啥", "干什么", "做什么", "做点啥", "充实", "无聊", "怎么过",
                                 "干啥好", "没意思", "空虚", "打发")):
        return True
    if find_area(u, config) and any(k in u for k in ("退休", "推荐", "建议", "好不好", "怎么样")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))
