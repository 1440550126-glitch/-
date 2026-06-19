"""人生节点寄语：孩子站在人生的坎上——高考、毕业、成家、生子、创业、退休——
那一刻，最想听见的是家里长辈那句过来人的话。把这份"言传身教"留住，随时给得出。

这是赛博永生很实在的一面：人不在了，那份叮嘱和祝福还在，赶得上每一个要紧的日子。
默认一套朴实的话，可在 config 按自家口吻覆盖。present-tense、纯逻辑、可单测。
"""

from __future__ import annotations

# 节点 → (触发词, 过来人的一段话)
_MILESTONES = {
    "高考": (["高考", "中考", "要考大学", "考大学", "高三"],
             "尽力就好，别给自己压太大。考场上稳住，会的别丢分，难的别慌。"
             "无论分数咋样，你都是我的骄傲——人生是长跑，这只是一程。"),
    "毕业": (["毕业", "毕业了", "拿到毕业证"],
             "十年寒窗，不容易。往后路自己走，记着：本事是真的，文凭是敲门砖。"
             "踏实做事，别怕从头学，肯学的人到哪儿都饿不着。"),
    "工作": (["找工作", "第一份工作", "入职", "新工作", "参加工作", "找了份工作", "找了工作"],
             "刚上班，多看多学少抱怨，手脚勤快点没人不喜欢。受点委屈是常事，"
             "扛过去就长本事。钱多钱少先别计较，先把人立住。"),
    "换工作": (["换工作", "跳槽", "辞职", "离职"],
               "想好了就走，别赌气走。骑驴找马稳当些，新地方先沉住气、把活干漂亮。"),
    "结婚": (["结婚", "要结婚了", "领证", "办婚礼", "成家", "我结婚"],
             "成家是大事，往后是两个人搭伙过日子。互相让着点，有话好好说，别记隔夜仇。"
             "祝你们和和美美，白头到老。"),
    "生子": (["生了", "生孩子", "当爸", "当妈", "添了", "怀孕", "有宝宝", "做父母"],
             "添丁了，大喜事！往后你就懂当爹妈的不容易了。别太累着自己，"
             "孩子健康快乐比啥都强，慢慢来，你们会是好父母。"),
    "买房": (["买房", "买了房", "付首付", "供房", "买套房"],
             "安了家，踏实。量力而行，别为了房子把日子过得太紧巴，"
             "屋子大小是其次，一家人和气才是真的家。"),
    "创业": (["创业", "开公司", "自己干", "做生意", "下海", "开店"],
             "想闯就去闯，年轻时不试会后悔。但别把老本都压上，留条退路。"
             "亏了也别怕，人没垮就还有机会，东山再起的人多了去了。"),
    "退休": (["退休", "退休了", "办了退休"],
             "忙了大半辈子，该歇歇了。可别闲出病来——找点爱好，多走动走动，"
             "把身体顾好。往后的日子，是给自己过的。"),
    "参军": (["参军", "当兵", "入伍", "去部队"],
             "去吧，是好样的。在部队听指挥、练真本事、护好自己，"
             "家里有我们，你只管安心。"),
    "出国": (["出国", "留学", "去国外", "出去念书"],
             "出门在外，照顾好自己，吃饱穿暖别硬撑。常打电话回来报个平安，"
             "钱不够言语一声，家永远是你的后盾。"),
    "本命年": (["本命年"],
               "本命年穿点红，图个吉利。别信那些晦气话，踏踏实实过这一年，平安顺遂。"),
    "失业": (["失业", "被裁", "下岗", "丢了工作", "被辞"],
             "丢了份工作不算啥，天塌不下来。歇两天，把心气养回来再找，"
             "你有手有脚有本事，这道坎一定迈得过去。家里有我们呢。"),
}


def milestones() -> list:
    return list(_MILESTONES.keys())


def _table(config) -> dict:
    db = {k: (list(v[0]), v[1]) for k, v in _MILESTONES.items()}
    if isinstance(config, dict) and isinstance(config.get("milestones"), dict):
        for k, v in config["milestones"].items():
            if isinstance(v, str) and v.strip():
                cues = db.get(k, ([k], ""))[0]
                db[k] = (cues if k in db else [k], v.strip())
            elif isinstance(v, dict) and v.get("words"):
                cues = v.get("cues") or db.get(k, ([k],))[0]
                if isinstance(cues, str):
                    cues = [cues]
                db[k] = ([str(c) for c in cues], str(v["words"]))
    return db


def detect_milestone(utterance, config=None) -> str:
    """认出说的是哪个人生节点；都不沾返回空。"""
    u = str(utterance or "")
    if not u:
        return ""
    best, best_len = "", 0
    for name, (cues, _words) in _table(config).items():
        for c in cues:
            if c and c in u and len(c) > best_len:   # 命中最长的那个，避免"工作"压过"换工作"
                best, best_len = name, len(c)
    return best


def blessing(milestone, name="", config=None) -> str:
    """给这个节点的一段过来人的话；认不出返回空。"""
    row = _table(config).get(milestone)
    if not row:
        return ""
    call = (str(name) + "，") if name else ""
    return call + row[1]


def for_utterance(utterance, name="", config=None) -> str:
    """从一句话里认出节点并给寄语；不是节点返回空。"""
    m = detect_milestone(utterance, config)
    return blessing(m, name, config) if m else ""
