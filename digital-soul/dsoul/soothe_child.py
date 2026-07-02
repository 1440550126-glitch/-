"""哄孩子：娃哭闹、不吃饭、不睡觉、摔倒了、认生——给爷爷奶奶爸爸妈妈支几招，
温和、不吼不吓，先接住情绪再想办法。带娃是门手艺，分身搭把手。

present-tense、纯逻辑、可单测。讲方法，不是替代专业育儿。
"""

from __future__ import annotations

# 情形 → (触发词, 温和的招)
_SITUATIONS = [
    {"name": "哭闹", "keys": ["哭闹", "孩子哭", "娃哭", "一直哭", "大哭", "闹脾气", "孩子闹"],
     "tip": "先蹲下来平视他，把人抱住、接住情绪——「我知道你难受」。等他平静些再慢慢问；"
            "别吼、别讲大道理，也可以指件新鲜东西转移一下注意力。"},
    {"name": "不吃饭", "keys": ["不吃饭", "不肯吃", "挑食", "喂不进", "不爱吃饭"],
     "tip": "别硬喂、别追着喂。把饭菜摆得有趣点，少盛勤添；和他比赛「看谁先吃完」，"
            "吃一口夸一口。这顿少吃点也没事，饿一饿下顿自然香。"},
    {"name": "不睡觉", "keys": ["不睡觉", "不肯睡", "不困", "闹觉", "哄睡"],
     "tip": "睡前固定一套小仪式：洗漱→讲个短故事→关大灯留小夜灯→轻拍哼支摇篮曲。"
            "睡前别玩太兴奋的，屋里光线调暗，慢慢就睡着了。"},
    {"name": "摔倒", "keys": ["摔倒", "摔了", "跌倒", "磕了"],
     "tip": "大人先别大惊小怪。平静地说「没事，自己站起来，真棒」，他多半就不哭了；"
            "再不动声色看看有没有真磕到、破皮，有伤再处理。"},
    {"name": "认生", "keys": ["认生", "怕生", "不叫人", "不打招呼", "躲生人"],
     "tip": "别强迫他喊人，那样越逼越躲。先抱着他、给点时间熟悉环境，"
            "大人聊得自然，孩子放松了自己就凑过去了。"},
    {"name": "抢玩具", "keys": ["抢玩具", "争玩具", "不分享", "抢东西"],
     "tip": "教「轮流玩」——「你先玩一会儿，再换给弟弟」，定个小规矩。"
            "别一味让大的让，两边都讲清楚，公平了就不闹了。"},
    {"name": "不刷牙", "keys": ["不刷牙", "不肯刷牙", "不洗澡", "不洗脸"],
     "tip": "编成游戏：「咱们把牙缝里的小虫子赶跑」。大人陪着一起刷做示范，"
            "用儿童牙刷、选他喜欢的图案，慢慢就愿意了。"},
    {"name": "黏人", "keys": ["太黏人", "黏人", "离不开", "一会儿看不见就哭"],
     "tip": "走之前好好告别、说清「妈妈办完事就回来」，别偷偷溜走（那样更没安全感）；"
            "回来一定兑现。慢慢拉长分开的时间，他就踏实了。"},
]


def situations() -> list:
    return [s["name"] for s in _SITUATIONS]


def find_situation(query) -> str:
    u = str(query or "")
    best, blen = "", 0
    for s in _SITUATIONS:
        for k in s["keys"]:
            if k in u and len(k) > blen:
                best, blen = s["name"], len(k)
    return best


def soothe(query) -> str:
    """娃这情形怎么哄。认不出返回空。"""
    name = find_situation(query)
    for s in _SITUATIONS:
        if s["name"] == name:
            return f"{s['tip']}"
    return ""


def is_child_soothing(utterance) -> bool:
    u = str(utterance or "")
    has_child = any(k in u for k in ("孩子", "娃", "宝宝", "小孩", "孙子", "孙女", "外孙", "带娃"))
    if has_child and any(k in u for k in ("怎么哄", "怎么办", "咋办", "不听话", "闹", "哭",
                                          "不吃", "不睡", "怎么带")):
        return True
    return bool(find_situation(u)) and any(k in u for k in ("怎么", "咋", "怎么办", "支招"))
