"""动动脑：陪老人练练脑子、防糊涂——口算、倒背数字、找不同、补老话。
不是考试，是图个"脑子常转不生锈"，顺带多陪一会儿。

纯逻辑、可单测：每道题给 (类型, 题目, 答案)，答案做成不带空格的串，
好让现成的"待答—核对"机制直接用。
"""

from __future__ import annotations


def _h(seed) -> int:
    return sum(ord(c) for c in str(seed)) + len(str(seed)) * 7


def math_drill(seed=""):
    """一道口算。返回 (题, 答案串)。"""
    h = _h(seed)
    a = 12 + h % 38
    b = 3 + (h // 5) % 9
    if h % 2 == 0:
        return (f"来道口算：{a} 加 {b} 等于几？", str(a + b))
    if b > a:
        a, b = b, a
    return (f"来道口算：{a} 减 {b} 等于几？", str(a - b))


def number_span(seed=""):
    """倒背数字。答案是连写的串（不带空格），方便核对。"""
    h = _h(seed)
    digits = [(h // (3 ** i)) % 10 for i in range(4)]
    q = " ".join(str(d) for d in digits)
    a = "".join(str(d) for d in reversed(digits))
    return (f"倒着报这串数（连着说、不用空格）：{q}", a)


_OOO = [
    (["苹果", "香蕉", "橘子"], "板凳"),
    (["猫", "狗", "兔子"], "卡车"),
    (["椅子", "桌子", "板凳"], "苹果"),
    (["红色", "黄色", "蓝色"], "圆形"),
    (["菊花", "荷花", "梅花"], "老虎"),
    (["馒头", "米饭", "面条"], "电视"),
]


def odd_one_out(seed=""):
    """找出不是一类的那个。"""
    members, intruder = _OOO[_h(seed) % len(_OOO)]
    items = members + [intruder]
    k = _h(seed) % len(items)
    items = items[k:] + items[:k]                  # 确定性地挪个位
    return (f"这几个里，哪个跟其他不是一类——{'、'.join(items)}？", intruder)


_PROV = [
    ("百闻不如", "一见"), ("功夫不负", "有心人"), ("活到老", "学到老"),
    ("一年之计在于", "春"), ("远亲不如", "近邻"), ("失败是成功之", "母"),
    ("书到用时", "方恨少"), ("良药苦口", "利于病"), ("一寸光阴", "一寸金"),
    ("众人拾柴", "火焰高"),
]


def proverb_fill(seed=""):
    """补全老话。"""
    a, b = _PROV[_h(seed) % len(_PROV)]
    return (f"补全这句老话：{a}——后半句是啥？", b)


_KINDS = (math_drill, number_span, odd_one_out, proverb_fill)


def a_drill(seed=""):
    """随机来一道。返回 (类型名, 题, 答案串)。"""
    f = _KINDS[_h(seed) % len(_KINDS)]
    q, a = f(seed)
    return (f.__name__, q, a)


def check(answer, a) -> bool:
    """核对（宽松：去掉空格标点后，一方含另一方即算对）。"""
    def norm(s):
        return "".join(ch for ch in str(s or "") if ch not in " ，,。.、！!？?")
    u, aa = norm(answer), norm(a)
    return bool(aa) and (aa in u or u in aa)


def is_brain_train(utterance) -> bool:
    u = str(utterance or "")
    return any(k in u for k in ("动动脑", "动脑筋", "动动脑子", "练脑", "记性操",
                                "脑力", "锻炼脑子", "练练脑", "出道题练", "考考脑子",
                                "做个脑筋操"))
