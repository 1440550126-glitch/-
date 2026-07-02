"""节庆食物的寓意：过年为啥吃年糕、饺子、鱼，端午粽子、冬至饺子——
这些吃食里藏着老百姓朴素的好彩头。提到哪样就讲讲它讨的什么口彩，节味儿更足。
纯逻辑、可单测。和"应季时鲜"(seasonal_food)、"节日筹备"(festival_prep)是一脉的吃货伙伴。
"""

from __future__ import annotations

# (食物, [别名], 寓意/讨的口彩)
_FOODS = [
    ("年糕", ["年糕"], "谐音'年年高'，盼日子、收入、个子一年比一年高。"),
    ("饺子", ["饺子", "水饺"], "形似元宝，'招财进宝';除夕吃取'更岁交子'(新旧交替)的意头。"),
    ("汤圆", ["汤圆", "元宵"], "圆滚滚、甜津津，一家人'团团圆圆'。"),
    ("鱼", ["鱼", "整鱼"], "谐音'余'，'年年有余';年夜饭这条鱼讲究剩一点、不吃完，留住富余。"),
    ("长寿面", ["长寿面", "寿面"], "面条长长，寓意'长命百岁';过生日、做寿都来一碗，面别咬断。"),
    ("春卷", ["春卷"], "金黄一卷像金条，'黄金万两、财源滚滚';立春、过年应景。"),
    ("八宝饭", ["八宝饭"], "糯米加红枣莲子等八样，甜甜糯糯，'团圆甜蜜、八方进宝'。"),
    ("月饼", ["月饼"], "圆如满月，中秋'阖家团圆、花好月圆'。"),
    ("粽子", ["粽子", "棕子"], "端午纪念屈原;'粽'谐音'中'，也讨'高中、功名'的彩头。"),
    ("腊八粥", ["腊八粥"], "腊八熬一锅五谷杂粮,'五谷丰登'，也暖身惜福。"),
    ("鸡", ["整鸡", "白切鸡", "鸡"], "谐音近'吉'，'大吉大利';年菜整鸡上桌讲究'有头有尾'。"),
    ("发糕", ["发糕", "发面", "馒头"], "'发'字讨彩，盼'发财、发家、日子蒸蒸日上'。"),
    ("苹果", ["苹果"], "'苹'谐音'平'，'平平安安';平安夜也爱送苹果。"),
    ("橘子", ["橘子", "桔子"], "'桔'近'吉'，红橘黄橙'大吉大利';过年摆一盘添喜气。"),
    ("红枣花生", ["红枣", "花生", "桂圆", "莲子", "枣"], "枣、生、桂、子凑'早生贵子'，婚嫁、添丁最爱摆。"),
    ("生菜", ["生菜"], "谐音'生财'，开年、开业图个'生财有道'。"),
]


def _all(config=None) -> list:
    items = list(_FOODS)
    cfg = (config or {}).get("festive_foods") if isinstance(config, dict) else None
    extra = (cfg or {}).get("items") if isinstance(cfg, dict) else None
    if isinstance(extra, list):
        for it in extra:
            if isinstance(it, (list, tuple)) and len(it) >= 3:
                items.append((str(it[0]), list(it[1]), str(it[2])))
            elif isinstance(it, dict) and it.get("name"):
                items.append((str(it["name"]), list(it.get("alias") or []), str(it.get("meaning", ""))))
    return items


def foods(config=None) -> list:
    return [f[0] for f in _all(config)]


def find_food(utterance, config=None):
    """提到了哪样节庆食物就揪出来（名/别名，最长匹配）。返回那条元组或 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for f in _all(config):
        for name in [f[0]] + list(f[1]):
            if name and name in u and len(name) > best_len:
                best, best_len = f, len(name)
    return best


def meaning(food, config=None) -> str:
    """某样节庆食物的寓意。查不到返回空。"""
    f = food if isinstance(food, tuple) else find_food(food, config)
    return f"{f[0]}的讲究：{f[2]}" if f else ""


def recall(seed="", config=None) -> str:
    """随口聊一样节庆吃食的彩头。"""
    items = _all(config)
    if not items:
        return ""
    f = items[len(str(seed)) % len(items)]
    return f"说样应景的——{f[0]}：{f[2]}"


def count(config=None) -> int:
    return len(_all(config))


def is_festive_food_query(utterance, config=None) -> bool:
    """是不是在问节庆食物的寓意。"""
    u = str(utterance or "")
    if any(k in u for k in ("过年吃什么", "年夜饭吃什么", "有什么讲究", "图什么彩头", "什么寓意的吃")):
        return True
    if find_food(u, config) and any(k in u for k in ("寓意", "为什么吃", "为啥吃", "讲究", "什么意思",
                                                     "什么彩头", "图个啥", "代表什么", "啥说法")):
        return True
    return False
