"""场景 / 例程：一句话触发一组设备动作（回家 / 睡眠 / 离家 / 影院）。

内置默认场景，可用 config/scenes.yaml 覆盖或新增。自然语言（含"我回来了"等别名）
解析为纯函数，零依赖、可单测。
"""

from __future__ import annotations

_DEFAULTS = {
    "回家模式": [["light", "on"], ["ac", "set", 26], ["music", "on"]],
    "睡眠模式": [["light", "off"], ["door", "off"]],
    "离家模式": [["light", "off"], ["ac", "off"], ["music", "off"], ["door", "off"]],
    "影院模式": [["light", "off"], ["tv", "on"]],
}
_ALIASES = {
    "我回来了": "回家模式", "回家了": "回家模式", "我到家了": "回家模式", "到家了": "回家模式",
    "睡觉了": "睡眠模式", "我要睡了": "睡眠模式", "晚安": "睡眠模式", "准备睡觉": "睡眠模式",
    "我出门了": "离家模式", "出门了": "离家模式", "我走了": "离家模式", "要出门了": "离家模式",
    "看电影": "影院模式", "看电视": "影院模式",
}


def parse_scene(text: str, names):
    """从一句话里识别场景（先匹配场景名，再匹配别名）。不是则返回 None。"""
    text = text or ""
    for n in names:
        if n in text:
            return n
    for alias, n in _ALIASES.items():
        if alias in text and n in names:
            return n
    return None


class SceneBook:
    def __init__(self, config=None) -> None:
        self.scenes = dict(_DEFAULTS)
        src = config.get("scenes") if isinstance(config, dict) else None
        if isinstance(src, dict):
            self.scenes.update(src)

    def names(self) -> list[str]:
        return list(self.scenes)

    def steps(self, name):
        return self.scenes.get(name)

    def run(self, name, devices):
        """执行场景的每一步，返回各步结果文案；场景不存在返回 None。"""
        steps = self.scenes.get(name)
        if steps is None or devices is None:
            return None
        msgs = []
        for step in steps:
            dev, act = step[0], step[1]
            val = step[2] if len(step) > 2 else None
            msgs.append(devices.control(dev, act, val).get("msg", ""))
        return msgs
