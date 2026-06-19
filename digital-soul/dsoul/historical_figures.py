"""历史名人：孔子、李白、诸葛亮、岳飞……他们是谁、哪个朝代、做了什么大事。
给孙辈讲讲，长志气、长见识。纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

# 名字 → (朝代, 身份与功绩)
_FIGURES = {
    "孔子": ("春秋", "儒家创始人，‘万世师表’，弟子三千，言行记在《论语》里。"),
    "老子": ("春秋", "道家创始人，著《道德经》，主张‘道法自然’。"),
    "孙子": ("春秋", "军事家孙武，著《孙子兵法》，‘知己知彼，百战不殆’。"),
    "屈原": ("战国", "楚国爱国诗人，著《离骚》，投江殉国，端午节就是纪念他。"),
    "秦始皇": ("秦", "统一六国、第一个称‘皇帝’，修长城、统一文字度量衡。"),
    "司马迁": ("西汉", "史学家，忍辱著《史记》，‘史家之绝唱，无韵之离骚’。"),
    "蔡伦": ("东汉", "改进了造纸术，让纸普及开来，四大发明之一。"),
    "张衡": ("东汉", "天文学家，发明地动仪，能测地震方向。"),
    "华佗": ("东汉", "神医，发明麻沸散做外科手术，创‘五禽戏’。"),
    "诸葛亮": ("三国", "蜀汉丞相，智慧的化身，‘鞠躬尽瘁，死而后已’，草船借箭、空城计。"),
    "关羽": ("三国", "忠义无双，被尊为‘武圣’，过五关斩六将。"),
    "王羲之": ("东晋", "‘书圣’，行书《兰亭序》号称‘天下第一行书’。"),
    "李白": ("唐", "‘诗仙’，浪漫飘逸，‘飞流直下三千尺’‘举头望明月’。"),
    "杜甫": ("唐", "‘诗圣’，忧国忧民，‘安得广厦千万间’。"),
    "武则天": ("唐", "中国历史上唯一的女皇帝，政绩颇有可观。"),
    "毕昇": ("北宋", "发明活字印刷术，四大发明之一。"),
    "包拯": ("北宋", "‘包青天’，铁面无私、断案如神，百姓敬仰。"),
    "岳飞": ("南宋", "抗金名将，‘精忠报国’，写下《满江红》，含冤而死。"),
    "郑和": ("明", "七下西洋，率庞大船队远航南洋、西洋，比哥伦布早几十年。"),
    "李时珍": ("明", "医药学家，遍尝百草著《本草纲目》。"),
    "曹操": ("三国", "魏的奠基人，政治家、军事家、诗人，‘老骥伏枥，志在千里’。"),
    "孟子": ("战国", "儒家‘亚圣’，主张‘民为贵’，‘老吾老以及人之老’。"),
    "墨子": ("战国", "墨家创始人，主张‘兼爱非攻’，还是个能工巧匠。"),
}

_ALIAS = {"孔夫子": "孔子", "诸葛孔明": "诸葛亮", "孔明": "诸葛亮", "诗仙": "李白",
          "诗圣": "杜甫", "书圣": "王羲之", "包青天": "包拯", "武圣": "关羽"}


def _table(config) -> dict:
    db = dict(_FIGURES)
    if isinstance(config, dict) and isinstance(config.get("figures"), dict):
        for k, v in config["figures"].items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                db[str(k)] = (str(v[0]), str(v[1]))
    return db


def figures(config=None) -> list:
    return list(_table(config))


def find_figure(query, config=None) -> str:
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for name in db:
        if name in u and len(name) > blen:
            best, blen = name, len(name)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def about(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_figure(query, config)
    row = db.get(name)
    if not row:
        return ""
    dyn, intro = row
    return f"{name}（{dyn}）：{intro}"


def is_figure_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if not find_figure(u, config):
        return False
    return any(k in u for k in ("是谁", "是什么人", "简介", "介绍", "什么朝代", "哪个朝代",
                                "做了什么", "什么人", "讲讲", "哪个年代", "干了什么", "是哪个"))
