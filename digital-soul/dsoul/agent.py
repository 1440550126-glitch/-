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
    def __init__(self, identity, persona, memory, authority, perception, llm, robot,
                 journal=None, emotions=None, knowledge=None, skills=None, hub=None) -> None:
        self.identity = identity
        self.persona = persona
        self.memory = memory
        self.authority = authority
        self.perception = perception
        self.llm = llm
        self.robot = robot
        self.journal = journal
        self.emotions = emotions     # 七情六欲情绪状态
        self.knowledge = knowledge   # 领域知识调度
        self.skills = skills         # 技能（做饭/家务…）
        self.hub = hub               # 外部智能体桥（爱马仕/openclaw…）

    def _hints(self) -> list[str]:
        out = []
        if self.emotions is not None:
            out.append(self.emotions.prompt_hint())
        if self.knowledge is not None:
            out.append(self.knowledge.prompt_hint())
        return [h for h in out if h]

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

        # --- 自然语言派活（如"让 openclaw 把代码打包"）---
        if action is None and self.hub is not None:
            disp = self.nl_dispatch(speaker_name, utterance)
            if disp is not None:
                result["reply"] = disp["reply"]
                result["dispatch"] = disp
                if self.journal is not None:
                    self.journal.append({
                        "speaker": who.get("name"), "speaker_relation": who.get("relation"),
                        "utterance": utterance, "reply": disp["reply"],
                        "executed": f"dispatch:{disp['agent']}",
                    })
                return result

        # --- 检索记忆 ---
        mems = [it["text"] for _, it in self.memory.recall(utterance, k=4)]
        result["memories"] = mems

        # --- 情绪随这句话起伏 ---
        if self.emotions is not None:
            self.emotions.observe(utterance, speaker=who if who.get("known") else None)

        # --- 生成回复（带上情绪 / 学识等提示）---
        system = self.persona.system_prompt(
            speaker=who if who.get("known") else None, memories=mems, hints=self._hints()
        )
        if self.llm.available:
            try:
                result["reply"] = self.llm.chat(system, utterance)
            except Exception as e:
                result["reply"] = self._fallback(who, utterance, mems) + f"\n（注：调用本地模型出错：{e}）"
        else:
            result["reply"] = self._fallback(who, utterance, mems)

        # --- 写入对话日记（短期记忆，供日后"睡眠巩固"）---
        if self.journal is not None:
            self.journal.append(
                {
                    "speaker": who.get("name"),
                    "speaker_relation": who.get("relation"),
                    "utterance": utterance,
                    "reply": result["reply"],
                    "executed": result.get("executed"),
                }
            )
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
                speaker=who if who.get("known") else None, memories=mems, hints=self._hints()
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

    # ---------- 技能：做饭 / 家务等（走授权闸门）----------
    def run_skill(self, speaker_name, skill_name, **params) -> dict:
        if self.skills is None:
            return {"ok": False, "msg": "未启用技能模块"}
        skill = self.skills.get(skill_name)
        if skill is None:
            return {"ok": False, "msg": f"没有这个技能：{skill_name}（可用：{', '.join(self.skills.names())}）"}
        ok, who, reason = self.authority.can(speaker_name, skill.permission)
        if not ok:
            return {"ok": False, "msg": reason, "who": who}
        return {"ok": True, "msg": skill.run(self, **params), "who": who}

    # ---------- 隔空指挥外部智能体（爱马仕 / openclaw…）----------
    def dispatch_agent(self, speaker_name, agent_name, task, **params) -> dict:
        ok, _who, reason = self.authority.can(speaker_name, "control_agents")
        if not ok:
            return {"ok": False, "error": reason}
        if self.hub is None:
            return {"ok": False, "error": "未配置外部智能体（见 config/agents.yaml）"}
        return self.hub.dispatch(agent_name, task, **params)

    # ---------- 自然语言派活（"让 openclaw 把代码打包"）----------
    def nl_dispatch(self, speaker_name, utterance) -> dict | None:
        """识别并执行"派活给外部智能体"的自然语言。不是派活则返回 None。"""
        if self.hub is None:
            return None
        from .remote_agents import parse_dispatch
        name = parse_dispatch(utterance, self.hub.names())
        if not name:
            return None
        ok, _who, reason = self.authority.can(speaker_name, "control_agents")
        if not ok:
            return {"dispatched": False, "agent": name, "reply": reason}
        res = self.hub.dispatch(name, "nl", instruction=utterance)
        if res.get("ok"):
            reply = f"好的，已经让「{name}」去办了。它回话：{res.get('result', '（无返回）')}"
        else:
            reply = f"我想交给「{name}」办，但没联系上它（{str(res.get('error', ''))[:30]}）。"
        return {"dispatched": bool(res.get("ok")), "agent": name, "result": res, "reply": reply}

    # ---------- 人格热切换（无需重启）----------
    def switch_persona(self, name, base_dir=None, seed_memory=False) -> dict:
        from .loader import reload_agent
        from .personas import apply_persona
        info = apply_persona(name, base_dir=base_dir, seed_memory=seed_memory)
        reload_agent(self, base_dir=base_dir)
        return info
