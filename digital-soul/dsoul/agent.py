"""智能体编排：把感知 / 记忆 / 人格 / 授权 / 大模型 / 机器人串成一个闭环。

主流程 handle()：
  1) 解析说话人身份（谁在跟我说话）
  2) 如果带动作请求 -> 先做授权检查（听不听、有没有权限），通过才让机器人执行
  3) 检索相关记忆
  4) 用人格 + 记忆 + 对话人组装提示词
  5) 本地大模型生成回复（没接模型则用记忆拼一个朴素回复）
"""

from __future__ import annotations

from collections import deque
from datetime import date, datetime

# 主动派活用的词表
_AFFIRM = ("好", "可以", "行", "嗯", "麻烦", "拜托", "去吧", "办", "对", "是的", "搞定", "就这么", "那就", "ok", "OK")
_NEGATE = ("不", "别", "算了", "先不", "不用", "甭")
_UNDONE = ("还没", "没弄", "没做", "还得", "还要", "忘了", "没空", "来不及", "没整", "没备份",
           "该弄", "得弄", "要弄", "没写", "堆着", "积压", "没处理", "没搞", "拖着")
_AGENT_HINTS = {"代码": "openclaw", "打包": "openclaw", "部署": "openclaw", "备份": "openclaw",
                "编译": "openclaw", "周报": "爱马仕", "报告": "爱马仕", "文档": "爱马仕",
                "整理": "爱马仕", "邮件": "爱马仕", "表格": "爱马仕"}
# 贾维斯式管家指令词
_BRIEF_KW = ("简报", "汇报", "报一下", "什么情况", "近况", "今天怎么安排", "今天的安排",
             "状态怎么样", "汇报一下", "brief")
_DIAG_KW = ("自检", "系统状态", "运行状况", "诊断", "各系统", "系统自检", "体检", "diagnostic", "status")


class Agent:
    def __init__(self, identity, persona, memory, authority, perception, llm, robot,
                 journal=None, emotions=None, knowledge=None, skills=None, hub=None,
                 tasks=None, reflector=None, planner=None, plan=None, devices=None,
                 scenes=None, triggers=None, sensor_source=None, dreams=None, selflog=None,
                 values=None, values_path=None, curiosity=None, worldmodel=None, calib=None) -> None:
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
        self.tasks = tasks           # 派活待办本（成/败都记，可主动跟进/重试）
        self._pending_dispatch = None  # 待你点头的"主动派活"提议
        self._await_retry_confirm = False  # 刚跟进过没办成的事，等你说"好"重试
        self.reflector = reflector   # 自主反思（记忆流 → 领悟）
        self._reflect_every = 8      # 每积累 8 条新经历自主反思一次
        self._last_reflect_len = len(journal._all()) if journal is not None else 0
        self.planner = planner       # 自主规划（领悟+欠账 → 今天打算做的事）
        self.plan = plan             # 当天计划（持久化）
        self.devices = devices       # 设备/家居控制（灯/空调/音乐…）
        self.scenes = scenes         # 场景/例程（回家/睡眠/离家…）
        self.triggers = triggers     # 自动化（定时 + 进门事件）
        self._sun_times = {"sunrise": "06:30", "sunset": "18:30"}  # 日出/日落（可配置）
        self.sensors = {"temperature": 22}                        # 模拟读数（无真实传感器时的兜底）
        self.sensor_source = sensor_source                        # 真实传感器源（如 HA），可为空
        self.dreams = dreams                                      # 梦境日志（睡眠时生成）
        self.selflog = selflog                                    # 自我成长史（每日一版）
        self.values = values                                      # 价值观（抉择时据此权衡）
        self.values_path = values_path                            # 演化后的价值权重持久化路径
        self.thoughts: deque = deque(maxlen=12)                   # 内心独白（近期心声）
        self.curiosity = curiosity                                # 好奇心：对陌生事物的疑问本
        self.worldmodel = worldmodel                              # 世界模型：带置信度的信念，会自我修正
        self.calib = calib                                        # 预测校准（从"猜对/没猜对"学习）
        self._last_prediction = None                              # 最近一次预感（供你反馈校准）
        self._pending_offer = None                                # 已主动提出、待你点头的预感
        self._briefed_on = None      # 今天是否已主动晨报过（按日期）

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

        # --- 主动派活的"二段确认"：上一轮我提议过，这一轮你说"好" → 执行 ---
        if action is None and self._pending_dispatch is not None:
            allowed = self.authority.can(speaker_name, "control_agents")[0]
            if allowed and self._is_affirm(utterance):
                done = self._run_pending_dispatch()
                result["reply"] = done["reply"]
                result["dispatch"] = done
                self._log_journal(who, utterance, done["reply"], f"dispatch:{done['agent']}")
                return result
            self._pending_dispatch = None  # 你没接这个茬，作罢

        # --- 主动预感的"接受"：上一轮我主动提了个预感，这一轮你说"好" ---
        if action is None and getattr(self, "_pending_offer", None) is not None:
            if who.get("obey") and self._is_affirm(utterance):
                reply = self._accept_offer(speaker_name)
                result["reply"] = reply
                self._log_journal(who, utterance, reply, "accept_offer")
                return result
            self._pending_offer = None  # 没接茬，作罢

        # --- 贾维斯式管家指令：点名应答 / 态势简报 / 系统自检（仅对听命于我的人）---
        if action is None:
            bret = self._butler_route(utterance, who)
            if bret is not None:
                result["reply"] = bret
                self._log_journal(who, utterance, bret, "butler")
                return result

        # --- 自动化设定（"每天22点提醒锁门" / "我一进门就开灯"）---
        if action is None and who.get("obey") and self.triggers is not None:
            tret = self._trigger_route(speaker_name, utterance)
            if tret is not None:
                result["reply"] = tret
                self._log_journal(who, utterance, tret, "trigger")
                return result

        # --- 场景 / 例程（"回家模式" / "我回来了"）---
        if action is None and who.get("obey"):
            sret = self._scene_route(speaker_name, utterance)
            if sret is not None:
                result["reply"] = sret
                self._log_journal(who, utterance, sret, "scene")
                return result

        # --- 多步任务编排（"把灯关了，再放点音乐" / "订会议并通知大家"）---
        if action is None and who.get("obey"):
            from .orchestrator import orchestrate
            multi = orchestrate(self, speaker_name, utterance, self._addr(who))
            if multi is not None:
                result["reply"] = multi
                self._log_journal(who, utterance, multi, "orchestrate")
                return result

        # --- 设备 / 家居控制（"把灯关了"）---
        if action is None and self.devices is not None:
            dmsg = self._device_route(speaker_name, utterance)
            if dmsg is not None:
                result["reply"] = dmsg
                self._log_journal(who, utterance, dmsg, "device")
                return result

        # --- 重试没办成的待办（"再试一次"，或刚跟进过你说"好"）---
        if action is None and self.tasks is not None and self.tasks.open():
            awaiting = self._await_retry_confirm
            self._await_retry_confirm = False
            kw = any(w in utterance for w in ("重试", "再试", "再来一次", "再弄一次", "再办一次"))
            if kw or (awaiting and self._is_affirm(utterance)):
                rr = self.retry_open(speaker_name)
                result["reply"] = rr["reply"]
                result["retry"] = rr
                self._log_journal(who, utterance, rr["reply"], "retry")
                return result

        # --- 自然语言派活（如"让 openclaw 把代码打包"）---
        if action is None and self.hub is not None:
            disp = self.nl_dispatch(speaker_name, utterance)
            if disp is not None:
                result["reply"] = disp["reply"]
                result["dispatch"] = disp
                self._log_journal(who, utterance, disp["reply"], f"dispatch:{disp['agent']}")
                return result

        # --- 主动派活：听出"有活儿没干"，主动提议（不擅自执行，等你点头）---
        if action is None and self.hub is not None:
            prop = self.propose_dispatch(speaker_name, utterance)
            if prop is not None:
                result["reply"] = prop["reply"]
                result["proposal"] = prop
                self._log_journal(who, utterance, prop["reply"], f"propose:{prop['agent']}")
                return result

        # --- 记忆图谱问答（"关于X" / "我的关系网" / "最核心的人"）---
        if action is None and who.get("obey"):
            gret = self._graph_route(utterance)
            if gret is not None:
                result["reply"] = gret
                self._log_journal(who, utterance, gret, "graph")
                return result

        # --- 预测反馈校准（"猜对了/没猜对"）：据此调整该信号的可信度 ---
        if action is None and who.get("obey") and getattr(self, "_last_prediction", None) and any(
                k in utterance for k in ("猜对", "猜准", "说对了", "真准", "说得对",
                                         "没猜对", "猜错", "没说对", "不太准", "蒙错")):
            correct = any(k in utterance for k in ("猜对", "猜准", "说对了", "真准", "说得对"))
            if self.calib is not None:
                self.calib.feedback(self._last_prediction.get("source", "?"), correct)
            self._last_prediction = None
            reply = "好，记下了，下次预感会更准。" if correct else "好，我调整一下，下次再蒙准点。"
            result["reply"] = reply
            self._log_journal(who, utterance, reply, "predict_feedback")
            return result

        # --- 信念解释（"你怎么看我/你眼中的我"）：说出理解 + 依据 ---
        if action is None and who.get("obey") and any(
                k in utterance for k in ("你怎么看我", "你眼中的我", "你对我的理解", "你了解我吗",
                                         "说说你对我", "你觉得我是", "你怎么理解我")):
            exp = self.explain_beliefs()
            if exp:
                result["reply"] = exp
                self._log_journal(who, utterance, exp, "explain_beliefs")
                return result

        # --- 好奇心自学（"去查一下/满足你的好奇"）：交给外部智能体学回来 ---
        if action is None and who.get("obey") and any(
                k in utterance for k in ("解答你的好奇", "去自学", "自己学一下", "查查你不懂",
                                         "满足你的好奇", "去查一下你")):
            got = self.self_learn()
            reply = ("我去查了查，学到：" + "；".join(f"{t}——{a[:24]}" for t, a in got)) if got \
                else "暂时没什么要查的，或者没联系上能帮我查资料的伙伴。"
            result["reply"] = reply
            self._log_journal(who, utterance, reply, "self_learn")
            return result

        # --- 群体模拟预测（"会不会/能成吗/靠谱吗"）：脑中开个小会拿主意 ---
        if action is None and who.get("obey") and any(
                k in utterance for k in ("会不会", "能不能成", "成不成", "能成", "成吗", "靠谱吗",
                                         "可行吗", "行不行", "你觉得会", "预测一下", "猜猜会", "模拟一下")):
            fc = self.forecast(utterance)
            result["reply"] = fc
            self._log_journal(who, utterance, fc, "forecast")
            return result

        # --- 价值抉择（"我该不该…/怎么选"）：据价值观给有立场的建议 ---
        if action is None and who.get("obey") and any(
                k in utterance for k in ("该不该", "应不应该", "纠结", "怎么选", "选哪个",
                                         "值得吗", "值不值", "两难", "该选", "怎么办好")):
            adv = self.deliberate(utterance)
            if adv:
                result["reply"] = adv
                self._log_journal(who, utterance, adv, "deliberate")
                return result

        # --- 检索记忆（强度感知：淡忘的更难想起；被用到的顺便强化）---
        recalled = self._recall(utterance, k=4)
        mems = [it["text"] for _, it in recalled]
        result["memories"] = mems
        if hasattr(self.memory, "reinforce"):
            self.memory.reinforce([it["id"] for _, it in recalled])

        # --- 量子纠缠：被想起的记忆"牵动"与之纠缠的记忆（测量其一即影响其二）---
        assoc = self._entangled_recall(recalled)
        result["associations"] = [t for _, t in assoc]
        ctx = mems + [t for _, t in assoc]

        # --- 情绪随这句话起伏 ---
        if self.emotions is not None:
            self.emotions.observe(utterance, speaker=who if who.get("known") else None)

        # --- 生成回复（带上情绪 / 学识等提示；上下文含纠缠联想）---
        system = self.persona.system_prompt(
            speaker=who if who.get("known") else None, memories=ctx, hints=self._hints()
        )
        if self.llm.available:
            try:
                result["reply"] = self.llm.chat(system, utterance)
            except Exception as e:
                result["reply"] = self._fallback(who, utterance, ctx) + f"\n（注：调用本地模型出错：{e}）"
        else:
            result["reply"] = self._fallback(who, utterance, ctx)

        # --- 内心独白：一闪而过的私密念头 ---
        thought = self._inner_thought(utterance, who, result.get("associations", []))
        result["thought"] = thought
        self.thoughts.append(thought)

        # --- 好奇心：听到陌生事物，心里默默记下"想问问" ---
        self._be_curious(utterance)
        # --- 世界模型自我修正：听到相反信号就动摇相应信念 ---
        self._maybe_correct_world(utterance)

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
        # 晨间主动简报：清晨第一次见到主人，主动汇报一次（不用你开口）
        if who.get("obey") and self._should_morning_brief():
            from .butler import daily_brief
            self._briefed_on = date.today().isoformat()
            text = f"{text} {daily_brief(self, present=[who['name']], addr=self._addr(who))}"
        # 主动跟进：见到能指挥智能体的人，顺口提一句没办成的事
        if self.authority.can(person_name, "control_agents")[0]:
            follow = self.follow_up_line()
            if follow:
                text = f"{text} {follow}"
                self._await_retry_confirm = True
        # 主动预感：见到你时，高置信的预感主动提一句
        if who.get("obey"):
            po = self.proactive_prediction()
            if po:
                text = f"{text} {po}"
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
        self._record_task(name, utterance, res)
        if res.get("ok"):
            self._remember_deed(name, utterance, res.get("result"))
            reply = f"好的，已经让「{name}」去办了。它回话：{res.get('result', '（无返回）')}"
        else:
            reply = f"我想交给「{name}」办，但没联系上它（{str(res.get('error', ''))[:30]}）。"
        return {"dispatched": bool(res.get("ok")), "agent": name, "result": res, "reply": reply}

    # ---------- 主动派活：听出有活儿没干就提议，点头才执行 ----------
    def propose_dispatch(self, speaker_name, utterance) -> dict | None:
        if self.hub is None:
            return None
        names = self.hub.names()
        if not names or not any(c in (utterance or "") for c in _UNDONE):
            return None
        if not self.authority.can(speaker_name, "control_agents")[0]:
            return None  # 只对能指挥智能体的人主动提议
        name = self._pick_agent(utterance, names)
        self._pending_dispatch = {"agent": name, "instruction": utterance, "speaker": speaker_name}
        reply = f"听起来这事儿还没着落。要不要我让「{name}」帮你办了？（说声“好”我就去办）"
        return {"proposed": True, "agent": name, "instruction": utterance, "reply": reply}

    def _run_pending_dispatch(self) -> dict:
        pd = self._pending_dispatch or {}
        self._pending_dispatch = None
        name, instr = pd.get("agent"), pd.get("instruction", "")
        res = self.hub.dispatch(name, "nl", instruction=instr)
        self._record_task(name, instr, res)
        if res.get("ok"):
            self._remember_deed(name, instr, res.get("result"))
            reply = f"好嘞，已经让「{name}」去办「{instr}」了。它回话：{res.get('result', '（无返回）')}"
        else:
            reply = f"我去找「{name}」办，但没联系上它（{str(res.get('error', ''))[:30]}）。"
        return {"dispatched": bool(res.get("ok")), "agent": name, "instruction": instr, "result": res, "reply": reply}

    @staticmethod
    def _is_affirm(text: str) -> bool:
        t = (text or "").strip()
        if any(n in t for n in _NEGATE):
            return False
        return any(a in t for a in _AFFIRM)

    @staticmethod
    def _pick_agent(text: str, names) -> str:
        for kw, who in _AGENT_HINTS.items():
            if kw in (text or "") and who in names:
                return who
        return names[0]

    def _log_journal(self, who, utterance, reply, executed) -> None:
        if self.journal is not None:
            self.journal.append({
                "speaker": who.get("name"), "speaker_relation": who.get("relation"),
                "utterance": utterance, "reply": reply, "executed": executed,
            })

    def _remember_deed(self, agent_name, instruction, result) -> None:
        """把"成功办成的事"写进长期记忆，让它日后记得、能主动跟进。"""
        text = f"我已让「{agent_name}」帮忙办了「{instruction}」（已完成）。"
        snippet = str(result or "").strip()[:50]
        if snippet:
            text += f"它回复：{snippet}"
        try:
            self.memory.add(text, source="dispatch", tags=["deed", "派活", agent_name])
        except Exception:
            pass

    def recent_deeds(self, k: int = 5) -> list[str]:
        """最近办成的事（供回顾 / 主动跟进）。"""
        deeds = [it["text"] for it in self.memory.items if "deed" in (it.get("tags") or [])]
        return deeds[-k:][::-1]

    def _record_task(self, agent_name, instruction, res) -> None:
        """把派活结果记进待办本：成功→关闭，失败→留作待办。"""
        if self.tasks is None:
            return
        detail = str(res.get("result") or res.get("error") or "")[:80]
        try:
            self.tasks.record(agent_name, instruction, bool(res.get("ok")), detail)
        except Exception:
            pass

    def follow_up_line(self) -> str:
        """一句"主动跟进"：提一件没办成的待办。没有就返回空串。"""
        if self.tasks is None:
            return ""
        op = self.tasks.open()
        if not op:
            return ""
        t = op[-1]
        return (f"对了，上次想让「{t['agent']}」办的「{t['instruction']}」还没办成"
                f"（试了 {t['attempts']} 次），要我再试一次吗？")

    def retry_open(self, speaker_name, cap: int = 99) -> dict:
        """重试没办成的待办（走 control_agents 授权）。cap：跳过尝试过多次的，避免死磕。"""
        if self.tasks is None or self.hub is None:
            return {"retried": 0, "ok": 0, "reply": "现在没有可重试的待办。"}
        allowed, _who, reason = self.authority.can(speaker_name, "control_agents")
        if not allowed:
            return {"retried": 0, "ok": 0, "reply": reason}
        op = [t for t in self.tasks.open() if t.get("attempts", 1) < cap]
        if not op:
            return {"retried": 0, "ok": 0, "reply": "没有没办成的事，都办妥啦。"}
        done = 0
        for t in op:
            res = self.hub.dispatch(t["agent"], "nl", instruction=t["instruction"])
            self._record_task(t["agent"], t["instruction"], res)  # 成功会就地关闭
            if res.get("ok"):
                self._remember_deed(t["agent"], t["instruction"], res.get("result"))
                done += 1
        if done == len(op):
            reply = f"都补上了：{done} 件待办全办成了。"
        elif done:
            reply = f"重试了 {len(op)} 件，办成 {done} 件，剩下的回头我再试。"
        else:
            reply = f"重试了 {len(op)} 件，还是没联系上，我先记着，过会儿再试。"
        return {"retried": len(op), "ok": done, "reply": reply}

    # ---------- 自主心跳：反思 → 规划 → 推进计划（由 daemon 定期调用）----------
    def tick(self, now=None) -> dict:
        out: dict = {"reflections": [], "plan": [], "notices": []}
        # 1) 自主反思（攒够新经历才反思，免得话痨）
        if self.reflector is not None and self.journal is not None:
            total = len(self.journal._all())
            if total - self._last_reflect_len >= self._reflect_every:
                self._last_reflect_len = total
                ref = self.reflector.reflect()
                if ref:
                    out["reflections"] = ref
                    out["notices"].append("我刚回想了一下，想明白几件事：" + "；".join(ref))
        # 2) 自主规划：每天排一次计划（领悟 + 欠账 + 心情 → 今天打算做的事）
        if self.planner is not None and self.plan is not None and not self.plan.fresh_today():
            mood = self.emotions.mood()[0] if self.emotions is not None else None
            open_tasks = self.tasks.open() if self.tasks is not None else []
            refl = self.recent_reflections()
            if refl or open_tasks:
                items = self.planner.make_plan(refl, open_tasks, mood)
                if items:
                    self.plan.set(items)
                    out["plan"] = [it["text"] for it in items]
                    out["notices"].append("我给今天列了个小计划：" + "；".join(out["plan"]))
        # 3) 推进计划：能办的去办，该提醒的提醒
        if self.plan is not None:
            out["notices"] += self._advance_plan()
        # 4) 温故：抢救正在淡忘的重要记忆
        rescued = self.rescue_fading()
        if rescued:
            out["notices"].append(f"我又温习了 {len(rescued)} 件要紧事，免得淡忘。")
        # 5) 记一版"今日之我"（自我成长史）
        if getattr(self, "selflog", None) is not None:
            try:
                self.selflog.record(self.self_narrative())
            except Exception:
                pass
        # 6) 梦的影响：反复梦见的人/事，醒来更上心（强化相关记忆）
        motifs = self.process_dream_influence()
        if motifs:
            out["notices"].append("我最近总梦到「" + "、".join(motifs) + "」，会多上点心。")
        # 7) 价值观随经历缓慢演化（三观随时间微调）
        if getattr(self, "values", None):
            self.evolve_values()
        # 8) 好奇心自学：把疑问交给外部智能体查一查
        if getattr(self, "curiosity", None) is not None and self.hub is not None:
            got = self.self_learn(max_q=1)
            if got:
                out["notices"].append("我自己查了查：" + "；".join(f"{t}→{a[:14]}…" for t, a in got))
        # 9) 更新世界模型（信念随证据增强）
        if getattr(self, "worldmodel", None) is not None:
            try:
                self.update_world()
            except Exception:
                pass
        # 10) 主动预感：高置信预感主动提一句
        po = self.proactive_prediction()
        if po:
            out["notices"].append("（预感）" + po)
        return out

    # ---------- 好奇心与世界模型 ----------
    def _be_curious(self, utterance) -> None:
        if self.curiosity is None:
            return
        from .annotate import classify_emotion
        from .curiosity import form_questions
        known = " ".join(it.get("text", "") for it in self.memory.items)
        importance = 0.3 if classify_emotion(utterance)["label"] != "平静" else 0.0  # 情绪重的更好奇
        if any(p.get("name") and p["name"] in utterance and p.get("trust") in ("owner", "family")
               for p in self.authority.people.values()):
            importance += 0.2                                   # 牵涉重要的人更好奇
        for q, term, pr in form_questions(utterance, known, importance):
            self.curiosity.add(term, q, pr)
        self.curiosity.resolve_known(known)          # 学到了的就销账

    def wonder(self) -> str:
        """挑一个还没问过的好奇，问回来（问完即标记已问）。没有则空。"""
        if self.curiosity is None:
            return ""
        op = self.curiosity.open()
        if not op:
            return ""
        q = op[0]
        self.curiosity.mark_asked(q["id"])
        return q["q"]

    def worldview(self, k: int = 6) -> list:
        """我眼中的世界：优先用带置信度的世界模型，否则现凑记忆图谱。"""
        if getattr(self, "worldmodel", None) is not None:
            top = self.worldmodel.top(k)
            if top:
                return [s for _, s in top]
        g = self.memory_graph()
        owner = self._owner_name()
        out = []
        for n, _ in g.central(10):
            meta = g.meta.get(n, {})
            if meta.get("kind") == "person" and n != owner:
                rel = meta.get("relation")
                out.append(f"{n}{('（' + rel + '）') if rel else ''}对你很重要")
            elif meta.get("kind") == "topic":
                out.append(f"你常挂念着「{n}」")
        return out[:k]

    def update_world(self) -> None:
        """从记忆图谱与价值观里印证信念（反复出现 → 越笃定）。"""
        if self.worldmodel is None:
            return
        g = self.memory_graph()
        owner = self._owner_name()
        for n, _ in g.central(8):
            meta = g.meta.get(n, {})
            if meta.get("kind") == "person" and n != owner:
                rel = meta.get("relation")
                self.worldmodel.reinforce(f"person:{n}", f"{n}{('（' + rel + '）') if rel else ''}对你很重要")
            elif meta.get("kind") == "topic":
                self.worldmodel.reinforce(f"topic:{n}", f"你很在意「{n}」")
        if getattr(self, "values", None):
            for name, v in sorted(self.values.items(), key=lambda kv: -kv[1].get("weight", 0))[:2]:
                self.worldmodel.reinforce(f"value:{name}", f"你看重「{name}」")

    def _maybe_correct_world(self, utterance) -> None:
        """听到相反信号（"其实不/不再/变了"…）就动摇相应信念——会改主意。"""
        if self.worldmodel is None:
            return
        neg = ("其实不", "不再", "已经不", "不喜欢", "不想", "不爱了", "变了", "错了", "不重要", "没那么")
        if not any(w in (utterance or "") for w in neg):
            return
        for key, b in list(self.worldmodel.beliefs.items()):
            topic = key.split(":", 1)[-1]
            if topic and topic in utterance:
                self.worldmodel.weaken(key, 2)

    def world_uncertain(self, k: int = 4) -> list:
        if getattr(self, "worldmodel", None) is None:
            return []
        return [s for _, s in self.worldmodel.shaky(k)]

    def anticipate(self, now=None) -> str:
        """情景预测：多信号 + 校准，预感这个点你可能想做什么；记住这条以便你反馈。"""
        if self.journal is None:
            return ""
        from .predict import predict
        p = predict(self.journal._all()[-200:], now=now, calib=getattr(self, "calib", None))
        self._last_prediction = p
        return p["label"] if p else ""

    def explain_beliefs(self, k: int = 3) -> str:
        """说出"我怎么看你"，并给出依据（举出支持的记忆）。"""
        if getattr(self, "worldmodel", None) is None:
            return ""
        top = self.worldmodel.top(k)
        if not top:
            return ""
        parts = []
        for conf, stmt in top:
            line = f"我{'挺确信' if conf >= 0.85 else '觉得'}{stmt}"
            ev = self._belief_evidence(stmt)
            if ev:
                line += f"——因为我记得「{ev}」"
            parts.append(line + "。")
        return "在我眼里，" + " ".join(parts)

    def _belief_evidence(self, stmt) -> str:
        import re
        m = re.search(r"「(.+?)」", stmt)
        ent = m.group(1) if m else stmt.split("（")[0].split("对你")[0].split("你看重")[-1].strip()
        for it in self.memory.items:
            if ent and ent in it.get("text", "") and "dream" not in (it.get("tags") or []):
                return it["text"][:30]
        return ""

    def self_learn(self, max_q: int = 2) -> list:
        """好奇心驱动自学：把疑问交给外部智能体去查，学到的写进记忆、销账。"""
        if self.curiosity is None or self.hub is None:
            return []
        names = self.hub.names()
        owner = self._owner_name()
        if not names or not owner or not self.authority.can(owner, "control_agents")[0]:
            return []
        learned = []
        for q in self.curiosity.open()[:max_q]:
            res = self.hub.dispatch(names[0], "nl", instruction="查一下并简短回答：" + q["q"])
            self.curiosity.mark_asked(q["id"])              # 问过即不反复（成败都标记）
            self._record_task(names[0], "查：" + q["term"], res)
            if res.get("ok"):
                ans = str(res.get("result", ""))[:120]
                self.memory.add(f"（学到）{q['term']}：{ans}", source="learned", tags=["learned"])
                learned.append((q["term"], ans))
        if learned:
            self.curiosity.resolve_known(" ".join(it.get("text", "") for it in self.memory.items))
        return learned

    # ---------- 内心独白 ----------
    def _inner_thought(self, utterance, who, assoc_texts) -> str:
        from .monologue import compose_thought
        mood_char = mood = None
        if self.emotions is not None:
            from .emotions import _DESC
            top, val = self.emotions.mood()
            if val >= self.emotions.baseline + 0.08:
                mood_char, mood = top, _DESC.get(top)
        return compose_thought(utterance, mood=mood, mood_char=mood_char, assoc=assoc_texts,
                               speaker=who.get("name") if who.get("known") else None)

    def forecast(self, question) -> str:
        """群体模拟预测：脑中开个小会，多视角各自表态（有大模型则真展开推理），聚合成预感。

        若几种思路分歧很大（认知多样性高），说明我自己也没把握——就记成高优先好奇，
        日后想弄明白（可被自学/问回来）。
        """
        from .swarm import forecast
        fc = forecast(question, llm=self.llm)
        if fc.get("diversity", 0) >= 0.5 and getattr(self, "curiosity", None) is not None:
            q = f"「{(question or '')[:18]}」这事我心里几种思路打架，挺想弄明白。"
            self.curiosity.add((question or "?")[:12] or "?", q, priority=0.9)
        return fc["text"]

    def proactive_prediction(self, now=None, min_conf: float = 0.7) -> str:
        """高置信预感主动提一句（并挂起，等你点头）。已提过未回应则不重复。"""
        if getattr(self, "_pending_offer", None) is not None:
            return ""
        label = self.anticipate(now=now)             # 顺带设好 _last_prediction
        lp = getattr(self, "_last_prediction", None)
        if label and lp and lp.get("confidence", 0) >= min_conf:
            self._pending_offer = lp
            return label
        return ""

    def _accept_offer(self, speaker_name) -> str:
        import re
        po = self._pending_offer or {}
        self._pending_offer = None
        m = re.search(r"「(.+?)」", po.get("label", ""))
        topic = m.group(1) if m else ""
        if self.scenes is not None and self.devices is not None and topic:
            from .scenes import parse_scene
            sc = parse_scene(topic, self.scenes.names())
            if sc:
                return self.run_scene(speaker_name, sc).get("msg", "好的")
        return f"好，那我留意着「{topic}」，到点提醒你。" if topic else "好，我记着了。"

    # ---------- 价值抉择 ----------
    def deliberate(self, text) -> str:
        from .values import deliberate as _deliberate
        return _deliberate(text, values=self.values,
                           guarded=self.authority.guarded_people(), llm=self.llm)

    def evolve_values(self) -> None:
        """从近期经历里统计各价值被触动的次数，缓慢演化权重并持久化。"""
        from collections import Counter

        from .values import evolve, relevant_values, save_state
        texts = []
        if self.journal is not None:
            texts += [e.get("utterance", "") for e in self.journal._all()[-30:]]
        texts += [it.get("text", "") for it in self.memory.items[-20:]]
        touched: Counter = Counter()
        for t in texts:
            for name, _ in relevant_values(t, self.values):
                touched[name] += 1
        evolve(self.values, touched)
        if self.values_path:
            try:
                save_state(self.values, self.values_path)
            except Exception:
                pass

    def recent_decisions(self, k: int = 5) -> list:
        """最近的价值抉择留痕：[(问题, 当时的建议), …]，回看"我是如何权衡的"。"""
        if self.journal is None:
            return []
        out = [(e.get("utterance", ""), e.get("reply", ""))
               for e in self.journal._all() if e.get("executed") == "deliberate"]
        return out[-k:][::-1]

    # ---------- 梦的影响 ----------
    def dream_motifs(self, k: int = 5) -> list:
        """近期梦里反复出现的人 / 事（出现在 ≥2 个梦里）。"""
        if getattr(self, "dreams", None) is None:
            return []
        from collections import Counter

        from .reflect import _bigrams
        names = [p.get("name") for p in self.authority.people.values() if p.get("name")]
        cnt: Counter = Counter()
        for r in self.dreams.recent(k):
            t = r.get("text", "")
            cnt.update({n for n in names if n and n in t} | set(_bigrams(t)))
        return [e for e, c in cnt.most_common() if c >= 2 and "梦" not in e and "场景" not in e][:3]

    def process_dream_influence(self) -> list:
        """反复梦见的，醒来更上心：强化相关记忆。返回这些主题。"""
        motifs = self.dream_motifs()
        if motifs and hasattr(self.memory, "reinforce"):
            ids = [it["id"] for it in self.memory.items
                   if any(m in it.get("text", "") for m in motifs)]
            if ids:
                self.memory.reinforce(ids)
        return motifs

    def _advance_plan(self) -> list:
        notices: list = []
        for it in self.plan.open():
            if it.get("kind") == "followup":
                inst = it.get("instruction", "")
                match = [o for o in (self.tasks.open() if self.tasks else []) if o.get("instruction") == inst]
                if not match:                          # 欠账已被补上 → 计划项完成
                    self.plan.mark_done(it["id"])
                    continue
                if match[0].get("attempts", 1) >= 6:   # 试太多次仍不行 → 搁置，别再纠缠
                    self.plan.mark_done(it["id"])
                    notices.append(f"「{inst}」试了多次还是没成，我先搁一搁。")
                    continue
                if self.hub is not None and self._owner_name():
                    res = self.hub.dispatch(it.get("agent"), "nl", instruction=inst)
                    self._record_task(it.get("agent"), inst, res)
                    if res.get("ok"):
                        self._remember_deed(it.get("agent"), inst, res.get("result"))
                        self.plan.mark_done(it["id"])
                        notices.append(f"计划里的「{inst}」办好了。")
            else:                                       # remind / checkin：提醒一次即完成
                self.plan.mark_done(it["id"])
                notices.append(it.get("text", ""))
        return notices

    def _owner_name(self):
        for p in self.authority.people.values():
            if p.get("trust") == "owner":
                return p["name"]
        return None

    def recent_reflections(self, k: int = 5) -> list[str]:
        """它最近想明白的事（领悟）。"""
        refl = [it["text"] for it in self.memory.items if "reflection" in (it.get("tags") or [])]
        return refl[-k:][::-1]

    def fading_memories(self, k: int = 5, now=None) -> list[tuple]:
        """正在淡忘的记忆（强度低、未被巩固的琐事）。返回 [(强度, 文本), …]。"""
        from .forgetting import strength
        scored = [(strength(it, now), it.get("text", "")) for it in self.memory.items]
        scored.sort(key=lambda x: x[0])
        return [(round(s, 2), t) for s, t in scored[:k] if s < 0.66]

    def _recall(self, text, k: int = 4, now=None):
        """强度感知检索：相关性 × (0.4 + 0.6×记忆强度)，淡忘的更难被想起。"""
        from .forgetting import strength
        cand = self.memory.recall(text, k=k * 3)
        ranked = sorted(cand, key=lambda si: -(si[0] * (0.4 + 0.6 * strength(si[1], now))))
        return ranked[:k]

    def dream(self) -> str:
        """睡眠时做一个梦：记忆碎片 + 情绪 + 纠缠联想重组成一段超现实叙事。"""
        if self.dreams is None:
            return ""
        from .dream import compose_dream
        mood = self.emotions.mood()[0] if self.emotions is not None else None
        names = [p.get("name") for p in self.authority.people.values()]
        extra = [t.strip("（）") for t in list(getattr(self, "thoughts", []))[-3:]]
        text = compose_dream(self.memory.items, mood=mood, names=names, llm=self.llm, extra=extra)
        if text:
            self.dreams.add(text, mood=mood)
            if self.emotions is not None and mood:
                self.emotions.feel({mood: 0.12})   # 梦的余韵：醒来还带着那点情绪
        return text

    def _entangled_recall(self, recalled):
        """对被回忆的记忆做扩散激活，牵动并强化与之纠缠的记忆。返回 [(强度, 文本), …]。"""
        try:
            from .entangle import spreading_activation
            names = [p.get("name") for p in self.authority.people.values()]
            assoc = spreading_activation([it for _, it in recalled], self.memory.items, names=names, k=2)
        except Exception:
            return []
        if assoc and hasattr(self.memory, "reinforce"):
            self.memory.reinforce([it["id"] for _, it in assoc])   # 测量牵动 → 强化纠缠伙伴
        return [(w, it.get("text", "")) for w, it in assoc]

    def rescue_fading(self, now=None, threshold: float = 0.35) -> list:
        """温故：抢救"重要但正在淡忘"的记忆（重温即强化），避免遗忘要紧事。"""
        from .forgetting import importance, strength
        if not hasattr(self.memory, "reinforce"):
            return []
        ids = [it["id"] for it in self.memory.items
               if importance(it) >= 0.6 and strength(it, now) < threshold]
        if ids:
            self.memory.reinforce(ids, now=now)
        return ids

    # ---------- 记忆图谱（人—事—主题 关系网）+ 自我意识叙事 ----------
    def self_narrative(self) -> str:
        """第一人称自我认知：身份 + 在乎的人 + 心情 + 领悟 + 怕忘的事 + 梦。"""
        from .forgetting import importance, strength
        from .selfnarrative import compose_self_narrative
        name = self.identity.get("name", "我")
        traits = "、".join((self.identity.get("personality", {}).get("traits") or [])[:3]) or None
        g = self.memory_graph()
        owner = self._owner_name()
        core = [n for n, _ in g.central(8)
                if g.meta.get(n, {}).get("kind") == "person" and n != owner][:3]
        mood_desc = None
        if self.emotions is not None:
            from .emotions import _DESC
            top, val = self.emotions.mood()
            if val >= self.emotions.baseline + 0.08:
                mood_desc = _DESC.get(top)
        refl = self.recent_reflections(1)
        imp_fading = sorted((it for it in self.memory.items if importance(it) >= 0.6),
                            key=lambda it: strength(it))
        cherished = imp_fading[0]["text"] if imp_fading and strength(imp_fading[0]) < 0.66 else None
        dream = None
        if getattr(self, "dreams", None) is not None:
            dr = self.dreams.recent(1)
            dream = dr[0]["text"] if dr else None
        return compose_self_narrative(name, core_people=core, mood_desc=mood_desc,
                                      insight=refl[0] if refl else None, cherished=cherished,
                                      dream=dream, traits=traits, llm=self.llm)

    def memory_graph(self):
        """构建/复用记忆图谱（记忆条数变化时才重建）。"""
        from .graph import build_memory_graph
        n = len(self.memory.items)
        cache = getattr(self, "_graph_cache", None)
        if cache and cache[0] == n:
            return cache[1]
        g = build_memory_graph(self.memory, self.authority)
        self._graph_cache = (n, g)
        return g

    def _graph_route(self, utterance):
        u = utterance or ""
        central = ("关系图谱", "关系网", "最重要的人", "最核心", "谁对我最重要", "我的人脉")
        entity = ("关于", "有关", "相关")
        if not any(k in u for k in central + entity):
            return None
        g = self.memory_graph()
        if any(k in u for k in central):
            top = [n for n, _ in g.central(5)]
            return ("在我的记忆里，最核心的是：" + "、".join(top) + "。") if top else "我还没攒够记忆来画关系网。"
        node = next((n for n in g.nodes() if n and n in u), None)
        if node:
            nb = "、".join(n for n, _ in g.neighbors(node, 5))
            msg = f"关于「{node}」，常和它一起出现的是：{nb or '（暂时还没有）'}。"
            about = g.about(node, 2)
            if about:
                msg += " 我记得：" + "；".join(about)
            return msg
        # 没有现成节点：抽取"关于X"的 X，退回实体检索
        key = u.split("关于", 1)[1] if "关于" in u else ""
        key = key.strip(" 的事都有还那些哪些什么怎样呢吗？?。.，,！!").strip()
        if key:
            hits = [it["text"] for _, it in self.memory.recall(key, k=3)]
            if hits:
                return f"关于「{key}」，我记得：" + "；".join(hits)
        return None

    # ---------- 贾维斯式管家层 ----------
    def _addr(self, who) -> str:
        """称呼：优先 identity.assistant.address（如"先生"），否则用对方名字。"""
        a = (self.identity.get("assistant") or {}).get("address")
        if a:
            return a
        if who and who.get("known"):
            return who.get("name", "您")
        return "您"

    def _butler_route(self, utterance, who):
        """识别管家指令：点名 / 简报 / 自检。不是则返回 None。仅服务于听命于我的人。"""
        u = utterance or ""
        if not who.get("obey"):
            return None  # 不对不听命于我的人汇报状态（隐私）
        low = u.lower()
        is_wake = ("贾维斯" in u) or ("jarvis" in low)
        if any(k in u for k in ("你是谁", "你是什么", "介绍一下你自己", "介绍下你自己",
                                "你眼中的自己", "认识一下自己", "你是怎样的存在", "你是个怎样")):
            return self.self_narrative()
        if any(k in u for k in _DIAG_KW):
            from .butler import diagnostics_text
            return diagnostics_text(self, self._addr(who))
        if any(k in u for k in _BRIEF_KW):
            from .butler import daily_brief
            present = [who["name"]] if who.get("known") else None
            return daily_brief(self, present=present, addr=self._addr(who))
        if is_wake:  # 点名但没具体吩咐 → 应答待命
            core = u.replace("贾维斯", "")
            for w in ("jarvis", "Jarvis", "JARVIS"):
                core = core.replace(w, "")
            if not core.strip("，,。.!！?？、 你好在吗不在呢啊呀嗨hi"):
                return f"在的，{self._addr(who)}。有什么吩咐？"
        return None

    def _should_morning_brief(self, now=None) -> bool:
        """清晨（5–11 点）且今天还没主动简报过。"""
        if self._briefed_on == date.today().isoformat():
            return False
        return 5 <= (now or datetime.now()).hour < 11

    # ---------- 设备 / 家居控制 ----------
    def device_control(self, speaker_name, device, action, value=None) -> dict:
        """直接控制某设备（网页按钮用），走 control_devices 授权。"""
        if self.devices is None:
            return {"ok": False, "msg": "未启用设备"}
        ok, _who, reason = self.authority.can(speaker_name, "control_devices")
        if not ok:
            return {"ok": False, "msg": reason}
        return self.devices.control(device, action, value)

    def _device_route(self, speaker_name, utterance):
        """识别设备指令并执行（走 control_devices 授权）。不是设备指令则返回 None。"""
        from .devices import parse_device_command
        cmd = parse_device_command(utterance)
        if not cmd:
            return None
        ok, _who, reason = self.authority.can(speaker_name, "control_devices")
        if not ok:
            return reason
        return self.devices.control(*cmd).get("msg", "好的")

    # ---------- 自动化（定时 + 进门事件）----------
    def _trigger_route(self, speaker_name, utterance):
        u = utterance or ""
        if any(w in u for w in ("取消所有自动化", "清空自动化", "取消所有提醒", "清空提醒", "清空所有自动化")):
            ok, _who, reason = self.authority.can(speaker_name, "control_devices")
            if not ok:
                return reason
            return f"好的，已清空 {self.triggers.clear()} 条自动化。"
        from .triggers import parse_trigger
        scene_names = self.scenes.names() if self.scenes is not None else []
        trig = parse_trigger(u, scene_names)
        if not trig:
            return None
        ok, _who, reason = self.authority.can(speaker_name, "control_devices")
        if not ok:
            return reason
        self.triggers.add(trig)
        return f"好的，已设定自动化：{trig['desc']}。"

    def _fire_action(self, action) -> str:
        t = action.get("type")
        if t == "device" and self.devices is not None:
            return self.devices.control(action["device"], action["act"], action.get("val")).get("msg", "")
        if t == "scene" and self.scenes is not None and self.devices is not None:
            self.scenes.run(action["name"], self.devices)
            return f"已启动「{action['name']}」"
        if t == "remind":
            return f"提醒：{action['text']}"
        return ""

    def check_time_triggers(self, now=None) -> list:
        """到点的定时触发（支持每天/每周/工作日/周末/日落日出；每条每天只触发一次）。"""
        if self.triggers is None:
            return []
        now = now or datetime.now()
        today, wd, hhmm = date.today().isoformat(), now.weekday(), now.strftime("%H:%M")
        notices = []
        for t in self.triggers.time_triggers():
            target = self._sun_times.get(t.get("spec"), t.get("spec"))   # 日落/日出 → HH:MM
            if target != hhmm:
                continue
            days = t.get("days")
            if days and wd not in days:                                  # 周期不匹配
                continue
            if t.get("last_fired") == today:
                continue
            self.triggers.mark_fired(t["id"], today)
            msg = self._fire_action(t.get("action", {}))
            if msg:
                notices.append(msg)
        return notices

    def read_sensors(self) -> dict:
        """当前传感器读数：优先真实源（如 HA），失败/未配置则用模拟读数。"""
        if getattr(self, "sensor_source", None) is not None:
            try:
                got = self.sensor_source.read()
                if got:
                    return got
            except Exception:
                pass
        return dict(getattr(self, "sensors", {}) or {})

    def check_conditions(self, readings=None) -> list:
        """条件触发（如温度低于阈值）。上升沿触发一次，避免反复。由 daemon 定时调用。"""
        if self.triggers is None:
            return []
        readings = readings if readings is not None else self.read_sensors()
        notices = []
        for t in self.triggers.cond_triggers():
            sp = t.get("spec", {})
            val = readings.get(sp.get("sensor"))
            if val is None:
                continue
            now_true = (val < sp["value"]) if sp["op"] == "<" else (val > sp["value"])
            if now_true and not t.get("state"):
                t["state"] = True
                self.triggers._save()
                msg = self._fire_action(t.get("action", {}))
                if msg:
                    notices.append(msg)
            elif (not now_true) and t.get("state"):
                t["state"] = False
                self.triggers._save()
        return notices

    def fire_event(self, event, who=None) -> list:
        """条件触发（如进门）。由 presence 进门回调调用。"""
        if self.triggers is None:
            return []
        notices = []
        for t in self.triggers.event_triggers(event):
            msg = self._fire_action(t.get("action", {}))
            if msg:
                notices.append(msg)
        return notices

    # ---------- 场景 / 例程 ----------
    def run_scene(self, speaker_name, name) -> dict:
        if self.scenes is None or self.devices is None:
            return {"ok": False, "msg": "未启用场景"}
        ok, _who, reason = self.authority.can(speaker_name, "control_devices")
        if not ok:
            return {"ok": False, "msg": reason}
        msgs = self.scenes.run(name, self.devices)
        if msgs is None:
            return {"ok": False, "msg": f"没有场景：{name}"}
        return {"ok": True, "msg": f"已启动「{name}」：" + "、".join(m for m in msgs if m)}

    def _scene_route(self, speaker_name, utterance):
        if self.scenes is None or self.devices is None:
            return None
        from .scenes import parse_scene
        name = parse_scene(utterance, self.scenes.names())
        if not name:
            return None
        return self.run_scene(speaker_name, name)["msg"]

    # ---------- 多步编排里的"执行单步" ----------
    def _exec_one_step(self, speaker_name, step):
        from .devices import parse_device_command
        from .remote_agents import parse_dispatch
        if self.devices is not None and parse_device_command(step):
            return self._device_route(speaker_name, step) or "（无法执行）"
        if self.hub is not None and self.hub.names():
            if parse_dispatch(step, self.hub.names()):
                d = self.nl_dispatch(speaker_name, step)
                return d["reply"] if d else "（无法派活）"
            r = self._dispatch_default(speaker_name, step)   # 没点名 → 交给默认智能体
            if r is not None:
                return r
        return f"记下了，到时提醒你「{step}」"

    def _dispatch_default(self, speaker_name, step):
        names = self.hub.names() if self.hub is not None else []
        if not names:
            return None
        ok, _who, reason = self.authority.can(speaker_name, "control_agents")
        if not ok:
            return reason
        name = names[0]
        res = self.hub.dispatch(name, "nl", instruction=step)
        self._record_task(name, step, res)
        if res.get("ok"):
            self._remember_deed(name, step, res.get("result"))
            return f"已交给「{name}」：{res.get('result', '已办')}"
        return f"想交给「{name}」办，但没联系上它"

    # ---------- 人格热切换（无需重启）----------
    def switch_persona(self, name, base_dir=None, seed_memory=False) -> dict:
        from .loader import reload_agent
        from .personas import apply_persona
        info = apply_persona(name, base_dir=base_dir, seed_memory=seed_memory)
        reload_agent(self, base_dir=base_dir)
        return info
