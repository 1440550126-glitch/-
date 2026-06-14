"""智能体编排：把感知 / 记忆 / 人格 / 授权 / 大模型 / 机器人串成一个闭环。

主流程 handle()：
  1) 解析说话人身份（谁在跟我说话）
  2) 如果带动作请求 -> 先做授权检查（听不听、有没有权限），通过才让机器人执行
  3) 检索相关记忆
  4) 用人格 + 记忆 + 对话人组装提示词
  5) 本地大模型生成回复（没接模型则用记忆拼一个朴素回复）
"""

from __future__ import annotations


class Agent:
    def __init__(self, identity, persona, memory, authority, perception, llm, robot) -> None:
        self.identity = identity
        self.persona = persona
        self.memory = memory
        self.authority = authority
        self.perception = perception
        self.llm = llm
        self.robot = robot

    def identify_speaker(self, image_path=None, video_path=None, name=None) -> str | None:
        """优先用人脸认人，认不出再用传入的名字。"""
        if image_path:
            n = self.perception.identify(image_path)
            if n:
                return n
        if video_path:
            n = self.perception.identify_video(video_path)
            if n:
                return n
        return name

    def handle(self, speaker_name: str | None, utterance: str, action: str | None = None) -> dict:
        who = self.authority.resolve(speaker_name)
        result: dict = {"who": who, "executed": None, "reply": "", "memories": [], "action_allowed": None}

        # --- 动作请求：先过授权这一关 ---
        if action:
            ok, who, reason = self.authority.can(speaker_name, action)
            result["who"] = who
            result["action_allowed"] = ok
            if not ok:
                result["reply"] = reason
                return result
            self._execute(action, who)
            result["executed"] = action

        # --- 检索记忆 ---
        mems = [it["text"] for _, it in self.memory.recall(utterance, k=4)]
        result["memories"] = mems

        # --- 生成回复 ---
        system = self.persona.system_prompt(
            speaker=who if who.get("known") else None, memories=mems
        )
        if self.llm.available:
            try:
                result["reply"] = self.llm.chat(system, utterance)
            except Exception as e:
                result["reply"] = self._fallback(who, utterance, mems) + f"\n（注：调用本地模型出错：{e}）"
        else:
            result["reply"] = self._fallback(who, utterance, mems)
        return result

    # ---------- 内部 ----------
    def _execute(self, action: str, who: dict) -> None:
        r = self.robot
        if action == "protect":
            target = who["name"] if who.get("guard") else (self.authority.guarded_people() or ["你"])[0]
            r.protect(target)
        elif action == "move":
            r.move("前", 1.0)
        elif action == "shutdown":
            r.say("好，我先休息了。")
        else:
            r.say(f"执行动作：{action}")

    def _fallback(self, who: dict, utterance: str, mems: list[str]) -> str:
        cps = self.identity.get("personality", {}).get("catchphrases", [])
        opener = (cps[0] + "，") if cps else ""
        if who.get("known"):
            addr = f"{who['name']}，"
            if who.get("guard"):
                addr = f"{who['name']}（放心，有我在）"
        else:
            addr = ""
        mem_part = (" 我想起来：" + "；".join(mems[:2]) + "。") if mems else ""
        tail = "（当前是降级模式：装好 Ollama 并 `ollama pull qwen2.5:7b-instruct` 后，我就能用完整性格和全部记忆回应了。）"
        return f"{opener}{addr}你说「{utterance}」，我听到了。{mem_part} {tail}"

    # ---------- 主动打招呼（由持续感知 presence 触发）----------
    def greet(self, person_name: str) -> str:
        who = self.authority.resolve(person_name)
        mems = [it["text"] for _, it in self.memory.recall(person_name or who["relation"], k=2)]
        if self.llm.available:
            system = self.persona.system_prompt(
                speaker=who if who.get("known") else None, memories=mems
            )
            prompt = f"{who['name']} 刚出现在你面前。请主动、自然地跟TA打个招呼，一句话就好。"
            try:
                text = self.llm.chat(system, prompt)
            except Exception:
                text = self._fallback_greet(who)
        else:
            text = self._fallback_greet(who)
        self.robot.say(text)
        return text

    def _fallback_greet(self, who: dict) -> str:
        name = who["name"]
        if not who.get("known"):
            return "你好，请问您是哪位？"
        if not who.get("obey"):
            return f"（看了一眼{name}，没有说话。）"
        if who.get("guard"):
            return f"{name}回来啦！我一直在等你呢。"
        if who.get("trust") == "family":
            return f"{name}，你来啦！"
        return f"嘿，{name}，好久不见！"
