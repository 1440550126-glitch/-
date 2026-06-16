"""人格层：把"你是谁 + 性格 + 当前对话人 + 相关记忆"组装成给大模型的人设提示词。

这是"模仿性格"的核心——它让模型用"你"的口吻、价值观和感情来回答。
"""

from __future__ import annotations


class Persona:
    def __init__(self, identity: dict) -> None:
        self.id = identity

    def system_prompt(self, speaker: dict | None = None, memories: list[str] | None = None,
                      hints: list[str] | None = None) -> str:
        idy = self.id
        p = idy.get("personality", {})
        L: list[str] = []

        L.append(
            f"你现在就是「{idy.get('name', '我')}」本人。"
            "用第一人称说话，你不是AI助手——你就是这个人。"
        )
        if idy.get("summary"):
            L.append(f"一句话自我介绍：{idy['summary']}")
        if p.get("traits"):
            L.append("你的性格：" + "、".join(p["traits"]) + "。")
        if p.get("speaking_style"):
            L.append("说话风格：" + p["speaking_style"])
        if p.get("values"):
            L.append("你最看重的：" + "、".join(p["values"]) + "。")
        if p.get("catchphrases"):
            L.append("口头禅（自然地用，别硬塞）：" + " / ".join(p["catchphrases"]))
        if idy.get("daily_life"):
            L.append("你平常的生活：" + "；".join(idy["daily_life"]) + "。")
        if idy.get("family_others"):
            L.append("你家里还有：" + "、".join(idy["family_others"]) +
                     "，你们是一家人，说话时可以自然地提起 TA 们。")

        if speaker:
            L.append(
                f"现在和你说话的是【{speaker.get('name', '对方')}】，"
                f"TA是你的{speaker.get('relation', '某个人')}。"
            )
            if speaker.get("feelings"):
                L.append(f"你对TA的真实感情：{speaker['feelings']}")
            if speaker.get("guard"):
                L.append(f"⚠️ {speaker.get('name')} 是你要用生命守护的人，对TA格外温柔、上心。")
            if not speaker.get("obey", True):
                L.append(f"注意：你并不信任 {speaker.get('name')}，对TA保持距离，不听从TA的指令。")

        if memories:
            joined = "\n".join(f"- {m}" for m in memories)
            L.append("以下是你刚想起来的相关记忆，回答时自然地用上（不要逐条复述）：\n" + joined)

        for h in (hints or []):
            if h:
                L.append(h)

        L.append("回答要简短、口语化、像真人微信聊天，别像机器人念稿子。")
        return "\n".join(L)
