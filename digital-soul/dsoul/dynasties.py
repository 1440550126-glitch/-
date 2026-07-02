"""历史朝代：背背朝代歌、理理朝代顺序，给孙辈讲讲哪个朝代有啥。
"夏商与西周，东周分两段……"——一首口诀串起五千年。

纯数据 + 纯逻辑、可单测。简介取广为人知的，挂一漏万。
"""

from __future__ import annotations

_SONG = ("夏商与西周，东周分两段；春秋和战国，一统秦两汉；"
         "三分魏蜀吴，二晋前后延；南北朝并立，隋唐五代传；"
         "宋元明清后，皇朝至此完。")

# 朝代 → (大致年代, 一句代表)
_DYNASTIES = [
    ("夏", "约前2070–前1600", "中国第一个王朝，相传大禹治水、传位启。"),
    ("商", "约前1600–前1046", "甲骨文、青铜器，盘庚迁殷。"),
    ("周", "前1046–前256", "分西周东周，行分封、重礼乐；孔子老子出于此时。"),
    ("春秋战国", "前770–前221", "诸侯争霸、百家争鸣，思想最灿烂的年代。"),
    ("秦", "前221–前207", "秦始皇统一六国，修长城、筑兵马俑、书同文。"),
    ("汉", "前202–220", "汉武盛世、张骞通西域、丝绸之路；分西汉东汉。"),
    ("三国", "220–280", "魏蜀吴鼎立，曹操、刘备、孙权、诸葛亮的年代。"),
    ("晋", "266–420", "分西晋东晋，王羲之、陶渊明出于此时。"),
    ("南北朝", "420–589", "南北分治、民族交融，石窟造像兴盛。"),
    ("隋", "581–618", "重新一统，开大运河、立科举。"),
    ("唐", "618–907", "盛世气象，李白杜甫、长安繁华，万国来朝。"),
    ("五代十国", "907–979", "唐宋之间的分裂动荡时期。"),
    ("宋", "960–1279", "经济文化鼎盛、宋词、四大发明多成于此；分北宋南宋。"),
    ("元", "1271–1368", "蒙古所建，疆域空前，马可·波罗来华。"),
    ("明", "1368–1644", "郑和下西洋、修紫禁城与长城，《本草纲目》成书。"),
    ("清", "1636–1912", "最后一个封建王朝，康乾盛世，后遭列强欺凌。"),
]

_ALIAS = {"西周": "周", "东周": "周", "西汉": "汉", "东汉": "汉", "两汉": "汉",
          "西晋": "晋", "东晋": "晋", "北宋": "宋", "南宋": "宋", "魏": "三国",
          "蜀": "三国", "吴": "三国", "春秋": "春秋战国", "战国": "春秋战国",
          "大唐": "唐", "大明": "明", "大清": "清", "强秦": "秦"}


def dynasty_song() -> str:
    return "朝代歌：" + _SONG


def dynasties() -> list:
    return [d[0] for d in _DYNASTIES]


def order() -> str:
    return " → ".join(d[0] for d in _DYNASTIES)


def find_dynasty(query) -> str:
    u = str(query or "")
    names = [d[0] for d in _DYNASTIES]
    best, blen = "", 0
    for n in names:
        if n in u and len(n) > blen:
            best, blen = n, len(n)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen:
            best, blen = real, len(a)
    return best


def about(dynasty) -> str:
    """某朝代的年代+代表。认不出返回空。"""
    d = find_dynasty(dynasty) or dynasty
    for name, era, intro in _DYNASTIES:
        if name == d:
            return f"{name}（{era}）：{intro}"
    return ""


def is_dynasty_query(utterance) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("朝代歌", "朝代顺序", "历史朝代", "朝代有哪些", "朝代排序")):
        return True
    if find_dynasty(u) and any(k in u for k in ("朝", "什么时候", "哪个年代", "介绍", "有什么",
                                                "是哪", "多少年", "讲讲")):
        return True
    return False
