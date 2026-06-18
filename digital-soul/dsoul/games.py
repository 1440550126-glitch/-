"""玩游戏：陪你猜谜、玩脑筋急转弯、来段成语接龙——图个乐子，让相处轻松有趣。
纯数据 + 纯逻辑、可单测。Agent 负责轮换记忆与对话衔接。
"""

from __future__ import annotations

_RIDDLES = [
    ("麻屋子，红帐子，里头住着白胖子。（打一食物）", "花生"),
    ("身穿绿衣裳，肚里水汪汪，生的子儿多，个个黑脸膛。（打一水果）", "西瓜"),
    ("白天一起玩，晚上一块眠，到老不分离，谁也不让谁。（打一身体部位）", "眼睛"),
    ("驼背老公公，胡须乱蓬蓬，活着就煮死，浑身红彤彤。（打一动物）", "虾"),
    ("远看像座亭，近看没窗棂，上面直流水，下面有人行。（打一物）", "雨伞"),
]

_BRAIN = [
    ("什么东西越洗越脏？", "水"),
    ("什么车寸步难行？", "风车"),
    ("一年四季都盛开的花是什么花？", "塑料花"),
    ("什么人始终不敢洗澡？", "泥人"),
    ("早上醒来，每个人都要做的第一件事是什么？", "睁开眼睛"),
]

# 首字 → 成语（用于成语接龙）
_IDIOMS = {
    "一": ["一帆风顺", "一鸣惊人", "一举两得"],
    "心": ["心想事成", "心花怒放"],
    "成": ["成竹在胸", "成人之美"],
    "美": ["美梦成真"],
    "真": ["真心实意"],
    "意": ["意气风发"],
    "万": ["万事如意", "万象更新"],
    "如": ["如愿以偿", "如日中天"],
    "顺": ["顺理成章", "顺水推舟"],
    "马": ["马到成功"],
    "功": ["功成名就"],
    "名": ["名正言顺"],
    "发": ["发愤图强"],
    "新": ["新年快乐"],
    "天": ["天遂人愿", "天长地久"],
}


def a_riddle(exclude=None):
    """出一道还没出过的谜语，返回 (题, 答案)。"""
    ex = set(exclude or [])
    pool = [r for r in _RIDDLES if r[0] not in ex] or _RIDDLES
    return pool[0]


def a_brainteaser(exclude=None):
    ex = set(exclude or [])
    pool = [b for b in _BRAIN if b[0] not in ex] or _BRAIN
    return pool[0]


def chain_from(idiom):
    """成语接龙：拿成语的末字，接一个以该字开头的成语；接不上返回空。"""
    s = str(idiom or "").strip()
    if not s:
        return ""
    last = s[-1]
    opts = _IDIOMS.get(last)
    return opts[0] if opts else ""


def looks_like_idiom(text) -> bool:
    """像不像一个四字成语（粗判：四个汉字）。"""
    s = str(text or "").strip()
    return len(s) == 4 and all("一" <= c <= "鿿" for c in s)


def is_game_request(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("玩游戏", "玩个游戏", "猜谜", "猜个谜", "脑筋急转弯",
                                "成语接龙", "来玩", "玩点啥"))


def detect_game(utterance) -> str:
    u = utterance or ""
    if "脑筋" in u or "急转弯" in u:
        return "脑筋急转弯"
    if "接龙" in u:
        return "成语接龙"
    if "谜" in u:
        return "猜谜"
    return "猜谜"
