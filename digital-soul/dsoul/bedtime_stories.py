"""睡前故事：给孙辈讲个温温柔柔的小故事，哄着睡。几则耳熟能详的老故事，
轮着讲不重样，末了一句"乖，闭上眼睛"。可在 config/bedtime.yaml 添自己的。纯逻辑、可单测。
"""

from __future__ import annotations

_STORIES = [
    {"title": "小马过河", "text": "小马要过河，松鼠说水深、老牛说水浅。它自己试着趟过去，"
                                   "才知道河水不深不浅，刚到膝盖。凡事啊，得自己试一试才知道。"},
    {"title": "龟兔赛跑", "text": "兔子跑得快，半路睡了大觉；乌龟慢吞吞，却一步不停。"
                                   "等兔子醒来，乌龟早到终点啦。慢不要紧，别停下就好。"},
    {"title": "司马光砸缸", "text": "小伙伴掉进大水缸里，别的孩子都吓跑了，"
                                     "只有司马光搬起石头把缸砸破，水流出来，人就得救了。遇事别慌，动动脑筋。"},
    {"title": "孔融让梨", "text": "孔融才四岁，分梨时挑了最小的一个，把大的让给哥哥弟弟。"
                                   "他说，我年纪小，就该吃小的。懂得谦让的孩子，人人都喜欢。"},
    {"title": "乌鸦喝水", "text": "乌鸦口渴，瓶里水浅够不着。它衔来一颗颗小石子丢进瓶里，"
                                   "水慢慢升高，就喝着啦。办法总比困难多。"},
]


def titles() -> list:
    return [s["title"] for s in _STORIES]


def collect(config=None) -> list:
    """内置故事 + config/bedtime.yaml 的 stories，按标题去重。"""
    out = list(_STORIES)
    seen = {s["title"] for s in out}
    for s in ((config or {}).get("stories") or []) if isinstance(config, dict) else []:
        if isinstance(s, dict) and s.get("title") and s.get("text") and s["title"] not in seen:
            out.append({"title": str(s["title"]).strip(), "text": str(s["text"]).strip()})
            seen.add(s["title"])
    return out


def pick(stories=None, exclude=None):
    """挑一个还没讲过的故事。"""
    pool = list(stories or _STORIES)
    ex = set(exclude or [])
    left = [s for s in pool if s["title"] not in ex] or pool
    return left[0] if left else None


def find(stories, query):
    """点名要听某个故事。"""
    q = str(query or "")
    for s in (stories or _STORIES):
        if s["title"] and s["title"] in q:
            return s
    return None


def tell(story) -> str:
    if not story:
        return ""
    return f"乖，闭上眼睛，给你讲《{story['title']}》——{story['text']} 好啦，睡吧，做个甜甜的梦。"


def is_request(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("讲个睡前故事", "睡前故事", "讲个故事哄", "哄睡", "讲故事哄",
                                "睡觉故事", "讲个小故事"))
