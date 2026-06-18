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
_CARE_KW = ("关怀简报", "晨间关怀", "早安简报", "今天要紧", "暖场白", "关心一下", "关怀一下")


class Agent:
    def __init__(self, identity, persona, memory, authority, perception, llm, robot,
                 journal=None, emotions=None, knowledge=None, skills=None, hub=None,
                 tasks=None, reflector=None, planner=None, plan=None, devices=None,
                 scenes=None, triggers=None, sensor_source=None, dreams=None, selflog=None,
                 values=None, values_path=None, curiosity=None, worldmodel=None, calib=None,
                 memorial=None, llm_router=None, legacy=None, care=None, family=None,
                 calendar=None, capsules=None, notes=None,
                 recipes=None, sayings=None, social=None, goals=None,
                 shopping=None, mannerisms=None, heirlooms=None,
                 health=None, favors=None, stories=None, teachings=None,
                 spouse=None, preferences=None, humor=None,
                 medications=None, safety=None, appointments=None,
                 opinions=None, joys=None) -> None:
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
        self.memorial = memorial or {}                            # 重要日子（缅怀/纪念）
        self.legacy = legacy or {}                                # 嘱托/家训（数字遗产）
        self.care = care or {}                                    # 守护对象的关照项（吃药/复查…）
        self._care_fired: set = set()                             # 当天已念过的守护提醒（去重）
        self.calendar = calendar                                  # 本地日程本（生日/复诊/约定）
        self.capsules = capsules                                  # 时光胶囊（封存给未来的话）
        self.notes = notes                                        # 速记便签（最轻的随手备忘）
        self.recipes = recipes or {}                              # 家传菜谱
        self.sayings = sayings or {}                              # 口头语录 / 老话
        self.mannerisms = mannerisms or {}                        # 说话习惯（神似：称呼/语气词/方言）
        self.heirlooms = heirlooms or []                          # 遗物/信物的故事与归属
        self.health = health or {}                                # 家族病史 / 过敏（救命的知识传承）
        self.favors = favors                                      # 人情往来账（礼尚往来）
        self.stories = stories or {}                              # 讲古：家史/往事故事库（配置）
        self._told_stories: set = set()                           # 已讲过的故事（轮着讲不重样）
        self.teachings = teachings or {}                          # 言传身教：道理 + 手艺
        self.spouse = spouse or {}                                # 老伴专属（夫妻之间：昵称/故事/唠叨/思念）
        self._spouse_nag_day = None                               # 当天是否已对老伴唠叨过（去重）
        self.preferences = preferences or {}                      # 喜好脾性（爱吃/偏爱/讨厌，答得稳）
        self.humor = humor or {}                                  # 幽默：段子库（讲过的轮换）
        self._told_jokes: set = set()                             # 已讲过的段子（去重）
        self.opinions = opinions or {}                            # 对人生话题的一贯看法（有主见）
        self.medications = medications                            # 用药守护（按时/续药/吃没吃）
        self.safety = safety or {}                                # 居家安全清单（睡前过一遍）
        self.appointments = appointments                          # 就医/约定提醒
        self._med_fired: set = set()                              # 已念过的吃药提醒（去重）
        self._appt_fired: set = set()                             # 已念过的就医提醒（去重）
        self.joys = joys                                          # 小确幸日记（攒开心事，翻出来念）
        self._joy_asked_day = None                                # 当天是否已主动问过开心事（去重）
        self._goodnight_day = None                                # 当晚是否已道过晚安（去重）
        self._ritual_fired: set = set()                           # 当天已唤过的日常默契（去重）
        self._companion_slot = None                               # 本时段是否已主动问候过（去重）
        self._wb_fired: set = set()                               # 当天各时段健康守护是否已提醒（去重）
        self._pending_cheer: dict = {}                            # 替家人惦记的大事（事后主动跟进）
        self.social = social                                      # 社交记忆（对每人的亲疏冷暖）
        self.goals = goals                                        # 心愿与目标
        self.shopping = shopping                                  # 采买清单
        self.family = family or {}                                # 多人合一：一宅多位家人
        self.active_member = None                                # 当前"叫出来"说话的是哪位家人
        self._home_identity = None                               # 切换前的本尊身份（可还原）
        self._home_persona = None
        self.llm_router = llm_router                              # 多模型路由（按任务选模型 + 小会面板）
        self._degraded_notice_shown = False                       # 降级提示只提一次
        self._briefed_on = None      # 今天是否已主动晨报过（按日期）

    def _hints(self) -> list[str]:
        from .style import style_hint
        out = []
        if self.emotions is not None:
            out.append(self.emotions.prompt_hint())
        if self.knowledge is not None:
            out.append(self.knowledge.prompt_hint())
        out.append(style_hint(self.identity))      # 用 TA 本人的口吻说话
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

        # --- 社交记忆：跟"认识的人"每打一次交道，更新这段关系的亲疏冷暖 ---
        if who.get("known") and getattr(self, "social", None) is not None:
            try:
                emo = self.emotions.mood()[0] if getattr(self, "emotions", None) else None
                topic = (utterance or "").strip()[:10] or None
                self.social.note(who["name"], emotion=emo, topic=topic)
            except Exception:
                pass

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

        # --- 老伴情感（最高优先）：另一半思念/睡不着 → 接住；闹脾气/委屈 → 哄好 ---
        if action is None and who.get("obey") and getattr(self, "spouse", None) \
                and self.is_my_spouse(who.get("name"), who.get("relation")):
            from .spouse import senses_longing, senses_upset
            txt, mark, topic = "", "", ""
            if senses_longing(utterance):
                txt, mark, topic = self.comfort_spouse(utterance), "spouse_comfort", "思念"
            elif senses_upset(utterance):
                txt, mark, topic = self.soothe_spouse(utterance), "spouse_soothe", "哄"
            if txt:
                result["reply"] = txt
                if self.social is not None:
                    self.social.note(who.get("name"), emotion="爱", topic=topic)
                self._log_journal(who, utterance, txt, mark)
                return result

        # --- 报喜：家人有了好消息，由衷替TA高兴（并记进里程碑）---
        # 排除"送什么礼/买什么礼"这类求助——那是要送礼参考，不是报喜
        if action is None and who.get("obey") and not any(
                k in (utterance or "") for k in ("送什么", "送啥", "买什么礼", "什么礼物", "挑个礼")):
            from .celebrate import detect_good_news
            if detect_good_news(utterance):
                txt = self.celebrate_news(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="喜", topic="喜事")
                    self._log_journal(who, utterance, txt, "celebrate")
                    return result

        # --- 小确幸：家人分享开心事，替TA记下、暖暖回应；问"念念开心事"则翻出来 ---
        if action is None and who.get("obey") and self.joys is not None:
            if any(k in (utterance or "") for k in ("念念开心", "最近开心的事", "有什么开心",
                                                    "翻翻开心", "回味", "开心的事")):
                txt = self.reflect_joys()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "joys_reflect")
                    return result
            from .joys import is_sharing_joy
            if is_sharing_joy(utterance):
                txt = self.record_joy(utterance, who=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="喜", topic="开心事")
                    self._log_journal(who, utterance, txt, "joy")
                    return result

        # --- 宽慰忧虑：家人说出担心/害怕，先认同那份不安，再轻轻宽慰 ---
        if action is None and who.get("obey"):
            from .worries import senses_worry
            if senses_worry(utterance):
                txt = self.comfort_worry(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="惧", topic="宽慰")
                    self._log_journal(who, utterance, txt, "worry")
                    return result

        # --- 打气：家人要面对大事，给句鼓励，事后还会主动跟进 ---
        if action is None and who.get("obey"):
            from .encourage import detect_occasion
            if detect_occasion(utterance):
                txt = self.cheer_on(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "encourage")
                    return result

        # --- 守护·用药（"我吃过药了" 记一笔；"我的药" 报一报）---
        if action is None and who.get("obey") and self.medications is not None:
            u = utterance or ""
            if any(k in u for k in ("我吃药了", "吃过药了", "药吃了", "我吃了药")):
                txt = self.take_med("降压药") or "好，记下了，吃过药了。"
                # 尽量认出具体药名
                for m in self.medications.meds:
                    if m["name"] in u:
                        txt = self.take_med(m["name"]) or txt
                        break
                result["reply"] = txt
                self._log_journal(who, u, txt, "med_taken")
                return result
            if any(k in u for k in ("我在吃什么药", "我的药", "在吃啥药", "吃哪些药")):
                txt = self.meds_describe()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "med_list")
                    return result

        # --- 守护·居家安全（"睡前检查一下" / "门窗关了吗"）---
        if action is None and who.get("obey"):
            from .safety_check import is_safety_query
            if is_safety_query(utterance):
                txt = self.safety_prompt()
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "safety")
                return result

        # --- 守护·就医约定（"我最近有什么安排" / "要复诊吗"）---
        if action is None and who.get("obey") and self.appointments is not None and any(
                k in (utterance or "") for k in ("有什么安排", "我的预约", "要复诊", "复诊",
                                                 "体检", "近期安排", "约了什么")):
            txt = self.appointments_describe()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "appointments")
                return result

        # --- 陪伴安慰（任何家人累了/难过了，以"我就在身边"接住，present-tense）---
        if action is None and who.get("obey"):
            from .companion import senses_down
            if senses_down(utterance):
                txt = self.present_comfort(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="哀", topic="陪伴")
                    self._log_journal(who, utterance, txt, "companion_comfort")
                    return result

        # --- 我们的故事 / 约定（"咱俩怎么认识的" / "我们的约定"）---
        if action is None and who.get("obey") and getattr(self, "spouse", None):
            us = utterance or ""
            if any(k in us for k in ("我们怎么认识", "咱俩怎么认识", "你们怎么认识", "怎么走到一起",
                                     "我们的故事", "你和妈怎么", "你跟妈怎么", "和妈妈怎么认识",
                                     "你俩怎么好上")):
                txt = self.love_story()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, us, txt, "love_story")
                    return result
            if any(k in us for k in ("我们的约定", "咱俩的约定", "答应过我", "说好的事", "我们说好")):
                txt = self.our_promises_line()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, us, txt, "promises")
                    return result
            if any(k in us for k in ("写封情书", "写封信", "给我写信", "写信给我", "写封家书",
                                     "给我写封")) and self.is_my_spouse(who.get("name"),
                                                                       who.get("relation")):
                occ = "纪念日" if "纪念" in us else ("思念" if "想" in us else "")
                txt = self.write_love_letter(occ)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, us, txt, "love_letter")
                    return result
            if any(k in us for k in ("晚安", "睡了", "睡觉了", "我去睡")) and \
                    self.is_my_spouse(who.get("name"), who.get("relation")):
                txt = self.goodnight_spouse()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, us, txt, "goodnight")
                    return result

        # --- 行为习惯（"你在干嘛/这会儿在做什么"）：说出 TA 此刻惯常的活动 ---
        if action is None and who.get("obey") and any(
                k in utterance for k in ("你在干嘛", "你在做什么", "这会儿在", "你现在忙", "在忙啥", "在干什么")):
            from .habits import current_activity
            from .style import apply_style
            act = current_activity(self.identity.get("daily_life"), )
            reply = apply_style(f"我这会儿一般{act}。" if act else "这会儿啊，就随便待着，陪陪你。", self.identity)
            result["reply"] = reply
            self._log_journal(who, utterance, reply, "habit")
            return result

        # --- 多人合一：报全家 / 把某位家人"叫出来"说话 / 请本尊回来 ---
        if action is None and who.get("obey") and self.family:
            from .family import find_member
            u = utterance or ""
            if any(k in u for k in ("我们家都有谁", "家里都有谁", "咱家都有谁", "家里有谁",
                                    "都有哪些人", "全家都有谁", "家里还有谁")):
                txt = self.family_roster()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "family_roster")
                    return result
            if self.active_member and any(k in u for k in ("你回来", "本尊", "换回来",
                                                           "还是你自己", "你自己来")):
                txt = self.restore_home()
                result["reply"] = txt
                self._log_journal(who, u, txt, "family_restore")
                return result
            if any(k in u for k in ("聊", "说说", "唠", "谈", "对话", "对谈")) and \
                    len(self.find_family_members(u)) >= 2:
                txt = self.let_them_talk(u)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "family_dialogue")
                    return result
            if any(k in u for k in ("叫来", "叫出来", "想和", "想跟", "我找", "在吗",
                                    "来说说", "来聊", "说说话", "出来说", "换成")):
                m = find_member(self.family, u)
                if m:
                    txt = self.become(u)
                    if txt:
                        result["reply"] = txt
                        self._log_journal(who, u, txt, f"become:{m.get('name')}")
                        return result

        # --- 编年生平 / 嘱托 / 家训 / 感恩遗憾（数字遗产）---
        if action is None and who.get("obey"):
            u = utterance or ""
            if any(k in u for k in ("你感恩", "最感念", "感激什么", "有什么遗憾", "你后悔",
                                    "放不下的", "这辈子值得", "这辈子最")):
                txt = self.reflect_gratitude()
                result["reply"] = txt
                self._log_journal(who, u, txt, "gratitude")
                return result
            if any(k in u for k in ("你的一生", "你这一生", "讲讲你的故事", "你的生平", "编年", "这辈子")):
                txt = self.life_chronicle() or "我这一生平平淡淡，倒也知足。"
                result["reply"] = txt
                self._log_journal(who, u, txt, "chronicle")
                return result
            if any(k in u for k in ("想对我说", "留给我的话", "嘱托", "遗言", "想叮嘱", "对我说的", "交代")):
                txt = self.deliver_last_words()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "last_words")
                    return result
            if any(k in u for k in ("家训", "家规", "老规矩", "家风")):
                txt = self.deliver_precepts()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "precepts")
                    return result
            if any(k in u for k in ("你希望我", "你对我的期望", "你盼着我", "对我的期许",
                                    "你希望我怎样", "期望我", "你盼我")):
                txt = self.deliver_wish(who.get("name") if who.get("known") else None)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "wish")
                    return result

        # --- 速记便签（"记个事：明天买菜" / "我的便签" / "清空便签"）---
        if action is None and who.get("obey") and self.notes is not None:
            u3 = utterance or ""
            if any(k in u3 for k in ("清空便签", "清空笔记", "删掉便签")):
                k = self.notes.clear()
                reply = f"好，{k} 条便签都清掉了。"
                result["reply"] = reply
                self._log_journal(who, u3, reply, "notes")
                return result
            if any(k in u3 for k in ("我的便签", "我的笔记", "看看便签", "看下便签",
                                     "便签有啥", "记了些什么")):
                rs = self.recent_notes()
                reply = ("便签：" + "；".join(rs)) if rs else "便签还空着呢。"
                result["reply"] = reply
                self._log_journal(who, u3, reply, "notes")
                return result
            if any(k in u3 for k in ("记个事", "记个笔记", "记条便签", "便签记", "记一笔", "帮我记下")):
                body = u3
                for kw in ("记个事", "记个笔记", "记条便签", "便签记", "记一笔", "帮我记下", "：", ":"):
                    body = body.replace(kw, "")
                reply = self.jot_note(body.strip("，,。.、 ")) or "想记点啥？说来听听。"
                result["reply"] = reply
                self._log_journal(who, u3, reply, "notes")
                return result

        # --- 采买清单（"买瓶酱油" / "鸡蛋买好了" / "采买清单"）---
        if action is None and who.get("obey") and self.shopping is not None:
            us = utterance or ""
            if any(k in us for k in ("采买清单", "购物清单", "买东西清单", "要买什么", "买啥",
                                     "清单上有啥", "采购清单")):
                reply = self.shop_list()
                result["reply"] = reply
                self._log_journal(who, us, reply, "shopping")
                return result
            done_kw = next((k for k in ("买好了", "买到了", "买完了", "划掉") if k in us), None)
            if done_kw:
                item = us.replace(done_kw, "").replace("把", "").strip("，,。.、 ")
                reply = self.shop_done(item)
                result["reply"] = reply
                self._log_journal(who, us, reply, "shopping")
                return result
            buy_kw = next((k for k in ("买瓶", "买袋", "买盒", "买点", "买个", "买斤", "买把",
                                       "记得买", "要买", "买") if k in us), None)
            if buy_kw and ("买" in us):
                item = us
                for kw in ("记得", "帮我", "顺便", "记一下", "再来", "再", "还", "也", "给我",
                           "我想", "想", "要", "买瓶", "买袋", "买盒", "买点", "买个", "买斤",
                           "买把", "买"):
                    item = item.replace(kw, "")
                item = item.strip("，,。.、吧啊呢 ")
                if item:
                    reply = self.shop_add(item)
                    result["reply"] = reply
                    self._log_journal(who, us, reply, "shopping")
                    return result

        # --- 触景生情 / 睹物思人（"说起老房子" / "看到这个就想起"）---
        if action is None and who.get("obey"):
            u = utterance or ""
            cue = None
            for mark in ("触景生情", "睹物思人"):
                if mark in u:
                    cue = u.replace(mark, "").strip("，,。.、 ") or "往事"
            import re as _re2
            m = _re2.search(r"(?:说起|提起|看到|想起了?|聊起)(.{1,12}?)(?:就|，|,|。|我|$)", u)
            if cue is None and m and ("想起" in u or "触景" in u or "睹物" in u
                                      or "说起" in u or "提起" in u):
                cue = m.group(1).strip("，,。.、 ")
            if cue:
                txt = self.reminisce_about(cue)
                result["reply"] = txt
                self._log_journal(who, u, txt, "reminisce")
                return result

        # --- 家传菜谱（"外婆的红烧肉怎么做" / "你有什么拿手菜"）---
        if action is None and who.get("obey") and self.recipes and (
                "怎么做" in (utterance or "") or "咋做" in (utterance or "")
                or "怎么烧" in (utterance or "") or "拿手菜" in (utterance or "")
                or "菜谱" in (utterance or "") or "会做什么菜" in (utterance or "")):
            txt = self.cook(utterance)
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "recipe")
                return result

        # --- 口头语录（"你常说什么" / "念几句你的老话"）---
        if action is None and who.get("obey") and self.sayings and any(
                k in (utterance or "") for k in ("你常说", "常挂嘴边", "你的老话", "你的语录",
                                                 "念几句", "口头禅是", "爱说的话")):
            txt = self.recite_sayings()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "sayings")
                return result

        # --- 说话习惯（"你说话有什么习惯" / "你的口音"）---
        if action is None and who.get("obey") and getattr(self, "mannerisms", None) and any(
                k in (utterance or "") for k in ("说话有什么习惯", "说话习惯", "怎么说话",
                                                 "你的口音", "你说话像", "口头习惯")):
            txt = self.speech_habits()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "mannerisms")
                return result

        # --- 遗物 / 信物（"爷爷那块表呢" / "有什么念想留给我"）---
        if action is None and who.get("obey"):
            uh = utterance or ""
            if (any(k in uh for k in ("遗物", "信物", "念想", "留给我", "传给我", "留了什么"))
                    or self._heirloom_hit(uh)):
                txt = self.heirloom_story(uh)
                if not txt and ("留给我" in uh or "传给我" in uh):
                    txt = self.bequests_for(who.get("name"))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, uh, txt, "heirloom")
                    return result

        # --- 家谱 / 辈分（"咱家几辈人" / "家谱"）---
        if action is None and who.get("obey") and self.family and any(
                k in (utterance or "") for k in ("家谱", "几辈人", "辈分", "家族树", "排排辈")):
            txt = self.family_tree_line()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "genealogy")
                return result

        # --- 纪念仪式（"带我们悼念" / "今天怎么纪念"）---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("纪念仪式", "悼念", "怎么纪念", "走个仪式",
                                                 "祭奠", "祭拜", "缅怀一下")):
            steps = self.remembrance_ritual()
            if steps:
                txt = "\n".join(steps)
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "anniversary")
                return result

        # --- 家族病史（"我身体要注意什么" / "咱家有什么遗传病"）---
        if action is None and who.get("obey") and getattr(self, "health", None) and any(
                k in (utterance or "") for k in ("身体要注意", "家族病史", "遗传病", "会遗传",
                                                 "家里有什么病", "要注意什么病", "我要当心什么")):
            txt = self.health_advice()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "health")
                return result

        # --- 节气时令（"今天什么节气" / "这节气要注意啥"）---
        if action is None and who.get("obey") and "节气" in (utterance or ""):
            txt = self.solar_term_line() or self.seasonal_wisdom()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "solar_term")
                return result

        # --- 人情往来（"人情账" / "咱欠谁的人情"）---
        if action is None and who.get("obey") and self.favors is not None and any(
                k in (utterance or "") for k in ("人情账", "人情往来", "欠谁的人情", "随礼往来",
                                                 "人情债", "礼尚往来")):
            txt = self.favor_ledger()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "favors")
                return result

        # --- 讲古 / 故事会（"讲个故事" / "想当年" / "讲个睡前故事"）---
        if action is None and who.get("obey"):
            us = utterance or ""
            if any(k in us for k in ("讲个故事", "讲故事", "讲古", "想当年", "讲讲以前",
                                     "讲讲过去", "说段往事", "睡前故事", "讲个事听")):
                bed = any(k in us for k in ("睡前", "睡觉", "哄睡", "哄我睡"))
                txt = self.tell_story(topic=us, bedtime=bed)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, us, txt, "story")
                    return result

        # --- 言传身教（"教我做人" / "教我包饺子" / "你有什么手艺"）---
        if action is None and who.get("obey") and getattr(self, "teachings", None):
            ut = utterance or ""
            if any(k in ut for k in ("教我", "教教", "做人的道理", "做人的理", "你那手艺",
                                     "什么手艺", "什么本事", "传授", "你的本事", "怎么为人")):
                txt = self.teach(ut)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, ut, txt, "teaching")
                    return result

        # --- 主见（"你怎么看熬夜" / "你觉得买房好不好"）：一贯的看法 ---
        if action is None and who.get("obey") and getattr(self, "opinions", None):
            from .opinions import is_opinion_query, match_topic
            if is_opinion_query(utterance) and match_topic(self.opinions, utterance):
                op = self.opine_on(utterance)
                if op:
                    result["reply"] = op
                    self._log_journal(who, utterance, op, "opinion")
                    return result

        # --- 内心活动（"你在想什么" / "想啥呢"）：把此刻心里的活动说出来 ---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("你在想什么", "想啥呢", "想什么呢",
                                                 "在想啥", "想什么呢", "发什么呆")):
            m = self.muse()
            if m:
                result["reply"] = m
                self._log_journal(who, utterance, m, "muse")
                return result

        # --- 脾性喜好（"你爱吃什么" / "你讨厌啥"）：答得稳，像有自己口味的人 ---
        if action is None and who.get("obey") and getattr(self, "preferences", None):
            pref = self.state_preference(utterance)
            if pref:
                result["reply"] = pref
                self._log_journal(who, utterance, pref, "preference")
                return result

        # --- 幽默（"讲个笑话" / 被打趣时俏皮回一句）---
        if action is None and who.get("obey"):
            from .humor import is_joke_request, is_teasing
            if is_joke_request(utterance):
                j = self.tell_a_joke()
                if j:
                    result["reply"] = j
                    self._log_journal(who, utterance, j, "joke")
                    return result
            if is_teasing(utterance):
                b = self.banter_back(utterance)
                result["reply"] = b
                self._log_journal(who, utterance, b, "banter")
                return result

        # --- 唠家常（"吃了吗" / "在吗" / "最近咋样"）：自然接住，别一本正经检索 ---
        if action is None and who.get("obey"):
            from .smalltalk import is_smalltalk
            if is_smalltalk(utterance):
                st = self.chitchat(utterance)
                if st:
                    result["reply"] = st
                    self._log_journal(who, utterance, st, "smalltalk")
                    return result

        # --- 陪聊：招呼"陪我聊聊"，主动挑个话头 ---
        if action is None and who.get("obey"):
            from .chat_starters import is_invite
            if is_invite(utterance):
                s = self.start_chat()
                if s:
                    result["reply"] = s
                    self._log_journal(who, utterance, s, "chat_start")
                    return result

        # --- 老话俗语（"说句老话" / "俗话说"）：挑句应景的，或成段背 ---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("说句老话", "有什么老话", "老话怎么说",
                                                 "老人言", "俗话说", "来句谚语", "讲句老话")):
            txt = self.drop_proverb(utterance) or self.recite_proverbs(utterance)
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "proverb")
                return result

        # --- 一起回忆（"还记得那回吗" / "想想以前"）：翻出和你的旧时光 ---
        if action is None and who.get("obey"):
            from .memory_lane import is_recall_invite
            if is_recall_invite(utterance):
                txt = self.recollect_with(who.get("name"), seed=utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "memory_lane")
                    return result

        # --- 送礼参考（"送爸什么礼物好" / "买什么礼"）---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("送什么礼", "送啥礼", "买什么礼", "买啥礼",
                                                 "送什么好", "挑个礼物", "送点什么", "送TA什么")):
            txt = self.suggest_gift(utterance)
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "gift")
                return result

        # --- 传统节日（"今天是什么节" / "端午有什么讲究"）---
        if action is None and who.get("obey"):
            u6 = utterance or ""
            if any(k in u6 for k in ("今天什么节", "今天是什么节", "今天有什么节", "什么节日",
                                     "今天过什么节")):
                line = self.festival_today() or "今天不是什么特别的节日，平常日子也要好好过。"
                result["reply"] = line
                self._log_journal(who, u6, line, "festival")
                return result
            if any(k in u6 for k in ("讲究", "习俗", "怎么过", "风俗", "祝福语")):
                info = self.festival_info(u6)
                if info:
                    result["reply"] = info
                    self._log_journal(who, u6, info, "festival")
                    return result

        # --- 亲戚称呼（"我爸的弟弟叫什么" / "妈妈的哥哥怎么称呼"）---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("叫什么", "叫啥", "怎么称呼", "该叫", "称呼",
                                                 "是我的什么", "算我什么")):
            from .kinship import parse_steps
            if len(parse_steps(utterance)) >= 1 and any(
                    w in (utterance or "") for w in ("爸", "妈", "哥", "弟", "姐", "妹",
                                                     "父", "母", "儿", "女", "夫", "妻")):
                txt = self.kinship(utterance)
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "kinship")
                return result

        # --- 社交记忆（"我跟小婷关系咋样" / "好久没见谁了"）---
        if action is None and who.get("obey") and getattr(self, "social", None) is not None:
            u4 = utterance or ""
            if any(k in u4 for k in ("好久没见", "好久没联系", "该联系", "久没见")):
                lines = self.long_unseen()
                reply = lines[0] if lines else "最近常来常往的人都见着了，挺好。"
                result["reply"] = reply
                self._log_journal(who, u4, reply, "social")
                return result
            if ("关系" in u4 and ("咋样" in u4 or "怎么样" in u4 or "好不好" in u4 or "亲" in u4)):
                for p in self.authority.people.values():
                    nm = p.get("name")
                    if nm and nm in u4 and nm != who.get("name"):
                        reply = self.relation_with(nm)
                        result["reply"] = reply
                        self._log_journal(who, u4, reply, "social")
                        return result

        # --- 心愿目标（"立个目标：每周陪爸妈吃饭" / "我的心愿" / "X做到了"）---
        if action is None and who.get("obey") and getattr(self, "goals", None) is not None:
            u5 = utterance or ""
            if any(k in u5 for k in ("我的目标", "我的心愿", "盘点目标", "盘一下目标",
                                     "目标进展", "还有什么没做")):
                reply = self.goals_summary()
                result["reply"] = reply
                self._log_journal(who, u5, reply, "goals")
                return result
            done_m = None
            for kw in ("做到了", "完成了", "达成了", "实现了"):
                if kw in u5:
                    done_m = u5.replace(kw, "").strip("，,。.、！ ")
                    break
            if done_m is not None:
                reply = self.complete_goal(done_m) or "这个目标我这儿没记着，不过做到了就好！"
                result["reply"] = reply
                self._log_journal(who, u5, reply, "goals")
                return result
            for kw in ("立个目标", "立个心愿", "记个心愿", "我想达成", "我的目标是", "定个目标"):
                if kw in u5:
                    body = u5.split(kw, 1)[-1].strip("，,。.：: ")
                    reply = self.set_goal(body) or "想达成点什么？说具体点我好记下。"
                    result["reply"] = reply
                    self._log_journal(who, u5, reply, "goals")
                    return result

        # --- 时光胶囊（"给孙女留句话，到2035年6月16日：好好长大"）---
        if action is None and who.get("obey") and self.capsules is not None:
            u2 = utterance or ""
            if ("时光胶囊" in u2 or "封存" in u2 or "留给未来" in u2
                    or ("留" in u2 and ("句话" in u2 or "几句" in u2))):
                import re as _rec
                md = _rec.search(r"(\d{4}\s*[-/年]\s*\d{1,2}\s*[-/月]\s*\d{1,2}\s*日?)", u2)
                msg = ""
                if "：" in u2 or ":" in u2:
                    msg = (u2.split("：", 1)[-1] if "：" in u2 else u2.split(":", 1)[-1]).strip()
                rec_m = _rec.search(r"给(.{1,8}?)(?:留|，|,|说|到|的|：|:|\d)", u2)
                recipient = rec_m.group(1).strip() if rec_m else (
                    who.get("name") if who.get("known") else "你")
                if md and msg:
                    cap = self.add_capsule(recipient, md.group(1).replace(" ", ""), msg)
                    reply = (f"好，这句话我替你封存了，到{cap['date']}再交给{cap['recipient']}。"
                             if cap else "日期没认出来，给个像 2035年6月16日 这样的日子吧。")
                else:
                    reply = "可以这样说：给孙女留句话，到2035年6月16日：好好长大。"
                result["reply"] = reply
                self._log_journal(who, u2, reply, "capsule")
                return result

        # --- 本地日程（"今天有什么事/日程" / "记一下6月18日去复诊"）---
        if action is None and who.get("obey") and self.calendar is not None and (
                "日程" in (utterance or "") or "安排吗" in (utterance or "")
                or any(k in (utterance or "") for k in ("今天有什么事", "今天有啥事", "今天有事吗",
                                                        "最近有什么事", "近几天有什么"))
                or (("记" in (utterance or "") or "提醒我" in (utterance or "") or "加个" in (utterance or ""))
                    and __import__("re").search(r"\d{1,2}\s*[-/月]\s*\d{1,2}", utterance or ""))):
            import re as _re
            mm = _re.search(r"(\d{4}\s*[-/年]\s*\d{1,2}\s*[-/月]\s*\d{1,2}\s*日?|\d{1,2}\s*[-/月]\s*\d{1,2}\s*日?)",
                            utterance or "")
            if mm:
                raw = mm.group(1).replace(" ", "")
                title = (utterance or "")
                for kw in ("记一下", "记下", "记到日程", "加个日程", "加到日程", "提醒我",
                           "日程", "记", "加个", "帮我", "去", raw):
                    title = title.replace(kw, "")
                title = title.strip("，,。.、 ")
                ev = self.add_event(title or "有件事", raw)
                reply = (f"好，记到日程了：{ev['date']} {ev['title']}。" if ev
                         else "这个日期我没认出来，换成像 6月18日 这样再说一次？")
            else:
                evs = self.today_events()
                reply = ("今天有：" + "、".join(evs) + "。") if evs else self.agenda_line()
            result["reply"] = reply
            self._log_journal(who, utterance, reply, "calendar")
            return result

        # --- 代笔家书（"给小婷写封信" / "替你给妈写封生日信"）---
        if action is None and who.get("obey") and (
                ("写" in (utterance or "") and "信" in (utterance or ""))
                or "代笔" in (utterance or "") or "家书" in (utterance or "")):
            recip = None
            cands = list(self.authority.people.values())
            try:
                from .family import members as _fm
                cands += _fm(self.family)
            except Exception:
                pass
            for p in cands:
                nm, rel = p.get("name"), p.get("relation")
                if (nm and nm in utterance) or (rel and rel in utterance):
                    recip = nm or rel
                    break
            if recip is None:
                recip = who.get("name") if who.get("known") else None
            letter = self.write_letter(recip, occasion=self._letter_occasion(utterance))
            result["reply"] = letter
            self._log_journal(who, utterance, letter, "letter")
            return result

        # --- 哀伤抚慰（家人表达思念）：以本人口吻、借共同回忆温柔回应 ---
        if action is None and who.get("obey"):
            from .memorial import comfort_reply, is_grief
            if is_grief(utterance):
                from .style import apply_style
                mems = [it["text"] for _, it in self._recall(utterance, k=2)]
                reply = apply_style(
                    comfort_reply(who.get("name") if who.get("known") else None, self.identity, mems),
                    self.identity)
                if self.emotions is not None:
                    self.emotions.feel({"爱": 0.2, "哀": 0.1})
                stage = self.grief_stage_line()          # 按"离开多久"再添一句贴合此刻的陪伴
                if stage:
                    reply = f"{reply} {stage}"
                result["reply"] = reply
                self._log_journal(who, utterance, reply, "comfort")
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
                k in utterance for k in ("集思广益", "问问大家", "大家觉得", "众人")):
            fed = self.federated_forecast(utterance)
            result["reply"] = fed
            self._log_journal(who, utterance, fed, "federated_forecast")
            return result
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
        from .style import apply_style
        if mems:
            body = f"{opener}{addr}我记得——{mems[0].rstrip('。.')}。" + \
                   (f" 还有，{mems[1].rstrip('。.')}。" if len(mems) > 1 else "")
        else:
            body = f"{opener}{addr}你说「{utterance}」，我都听着呢。"
        out = apply_style(body, self.identity)
        if not getattr(self, "_degraded_notice_shown", False):     # 技术提示只出现一次
            self._degraded_notice_shown = True
            out += "\n（小提示：接上本地 Ollama 后，我能用完整性格和全部记忆回应。）"
        return out

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
        # 纪念日：温和地提一句"今天是个特别的日子"，不主动提及生死、不念临别赠言（免得吓到人）
        if who.get("obey"):
            occ = self.memorial_today()
            if occ:
                text = f"{text} 对了，今天是{'、'.join(occ)}，是个值得记着的日子。"
        # 主动预感：见到你时，高置信的预感主动提一句
        if who.get("obey"):
            po = self.proactive_prediction()
            if po:
                text = f"{text} {po}"
        # 守护提醒：见到你时，若此刻惦记的家人该吃药/复查，顺口叮嘱一句
        if who.get("obey"):
            for c in self.due_care():
                text = f"{text} {c}"
        # 时光胶囊：到开封日了，把封存的话郑重交给该交的人
        if who.get("obey"):
            for cap in self.due_capsules():
                text = f"{text} {cap}"
        # 老伴专属：见到另一半，纪念日道一声/提前提醒、日常默契、把牵挂的话轻轻唠叨（当天去重）
        if who.get("obey") and getattr(self, "spouse", None) \
                and self.is_my_spouse(who.get("name"), who.get("relation")):
            anni = self.spouse_anniversary()
            if anni:
                text = f"{text} {anni}"
            else:
                cd = self.spouse_anniversary_countdown()
                if cd:
                    text = f"{text} {cd}"
            rit = self.spouse_ritual_now()
            if rit:
                text = f"{text} {rit}"
            for c in self.spouse_care_today():
                text = f"{text} {c}"
        # 家谱生日：见到你时，若近几天有家人过生日，主动提醒一句别忘了
        if who.get("obey") and self.family:
            bday = self.birthday_reminders(within=7)
            if bday:
                text = f"{text} {bday}"
        # 节气时令：今天恰逢节气，像家里老人那样顺口叮嘱一句
        if who.get("obey"):
            st = self.solar_term_line()
            if st:
                text = f"{text} {st}"
        # 打气跟进：之前替你惦记的大事（考试/面试/手术…），过后主动问一句结果
        if who.get("obey"):
            fu = self.cheer_followup(who.get("name"))
            if fu:
                text = f"{text} {fu}"
        # 陪伴：按这个时候，顺口关心一句（本时段当天只问一次，不啰嗦）
        if who.get("obey"):
            ci = self.companion_checkin()
            if ci:
                text = f"{text} {ci}"
        self.robot.say(text)
        return text

    def memorial_today(self, now=None) -> list:
        from .memorial import today_occasions
        return today_occasions((self.memorial or {}).get("dates", {}), now)

    # ---------- 守护提醒：惦记家人的吃药 / 复查 ----------
    def due_care(self, now=None) -> list:
        """此刻该叮嘱家人的话（吃药到点 / 今天该复查），当天去重不重复念。"""
        from .guardian import due_reminders
        now = now or datetime.now()
        day = now.strftime("%Y-%m-%d")
        out = []
        for text in due_reminders(self.care, now):
            key = (day, text)
            if key in self._care_fired:
                continue
            self._care_fired.add(key)
            out.append(text)
        return out

    def care_briefing(self, name=None, now=None) -> str:
        """晨间关怀简报：今天什么日子 + 谁该吃药复查 + 今天打算 + 一句暖场白。"""
        from .briefing import compose_briefing
        from .festival import festival_on
        from .guardian import due_reminders
        from .legacy import last_words
        occ = list(self.memorial_today(now))
        fest = festival_on(now)
        if fest:
            occ = [fest] + occ
        care = list(due_reminders(self.care, now)) if self.care else []
        agenda = list(self.today_events(now))
        if getattr(self, "plan", None) is not None:
            agenda += [it.get("text", "") for it in self.plan.items
                       if it.get("status") != "done"]
        agenda = agenda[:3]
        encouragements = ["今天也要好好吃饭、好好睡觉。", "慢慢来，我都在。",
                          "别太累，记得歇一歇。", "想我了就跟我说说话。"]
        idx = (now or datetime.now()).toordinal() % len(encouragements)
        return compose_briefing(name=name, occasions=occ, care=care, agenda=agenda,
                                last_words=last_words(self.legacy), now=now,
                                encouragement=encouragements[idx])

    def write_letter(self, recipient_name, occasion=None) -> str:
        """以 TA 本人的口吻给某位家人写一封信（可指定场合）。"""
        from .letters import compose_letter
        who = self.authority.resolve(recipient_name) if recipient_name else {}
        relation = who.get("relation") if who.get("known") else None
        cps = self.identity.get("personality", {}).get("catchphrases", [])
        mems = [it["text"] for _, it in self._recall(recipient_name or "我们", k=2)] \
            if recipient_name else []
        return compose_letter(
            sender_name=self.identity.get("name", "我"), catchphrases=cps,
            recipient_name=recipient_name, recipient_relation=relation,
            occasion=occasion, memories=mems, llm=self.llm)

    def _letter_occasion(self, text) -> str | None:
        for occ in ("生日", "过年", "想念", "道歉", "鼓励", "感谢"):
            if occ in (text or ""):
                return occ
        return None

    # ---------- 本地日程：记事 / 今天有什么 / 最近几天 ----------
    def add_event(self, title, date, kind="事") -> dict | None:
        if self.calendar is None:
            return None
        return self.calendar.add(title, date, kind)

    def today_events(self, now=None) -> list:
        cal = getattr(self, "calendar", None)
        return cal.describe_today(now) if cal is not None else []

    def agenda_line(self, now=None) -> str:
        """今天的日程一句话；空则给一句轻松的。"""
        evs = self.today_events(now)
        if evs:
            return "今天有：" + "、".join(evs) + "。"
        cal = getattr(self, "calendar", None)
        up = cal.upcoming(7, now) if cal is not None else []
        if up:
            from .calendar_book import days_until
            e = up[0]
            n = days_until(e["date"], now or datetime.now())
            when = "明天" if n == 1 else (f"{n}天后" if n else "今天")
            return f"近几天：{when}是{e['title']}。"
        return "今天没什么特别安排，轻松点。"

    # ---------- 时光胶囊：封存给未来的话 ----------
    def add_capsule(self, recipient, deliver_date, message) -> dict | None:
        cap = getattr(self, "capsules", None)
        return cap.add(recipient, deliver_date, message) if cap is not None else None

    def due_capsules(self, now=None) -> list:
        """到点开封的时光胶囊，说成郑重的交付（只送一次）。"""
        cap = getattr(self, "capsules", None)
        if cap is None:
            return []
        return [cap.speak(c) for c in cap.due(now)]

    # ---------- 临别期许 ----------
    def deliver_wish(self, name) -> str:
        """说出 TA 对某位家人的期望/祝愿（配在 legacy.wishes 或 family 成员 wish）。"""
        from .style import apply_style
        from .wishes import collect_wishes, wish_for
        w = wish_for(collect_wishes(self.legacy, self.family), name)
        if not w:
            return ""
        return apply_style(f"我对你啊，没别的，就盼着：{w}", self.identity)

    # ---------- 速记便签 ----------
    def jot_note(self, text) -> str:
        n = getattr(self, "notes", None)
        if n is None:
            return ""
        note = n.add(text)
        return f"记下了：{note['text']}" if note else ""

    def recent_notes(self, k=8) -> list:
        n = getattr(self, "notes", None)
        return n.recent(k) if n is not None else []

    # ---------- 家传菜谱 / 口头语录 ----------
    def cook(self, query) -> str:
        """照着 TA 的方子说一道菜；问"有什么拿手菜"则报菜名。"""
        from .recipes import collect_recipes, find_recipe, list_names, recipe_text
        rs = collect_recipes(self.recipes, self.family)
        if not rs:
            return ""
        if any(k in (query or "") for k in ("拿手菜", "会做什么", "会做啥", "都会做", "菜谱")):
            names = list_names(rs)
            return ("我拿手的有：" + "、".join(names) + "。想吃哪个？") if names else ""
        r = find_recipe(rs, query)
        return recipe_text(r) if r else ""

    def recite_sayings(self, topic=None) -> str:
        from .sayings import collect_sayings, recite
        return recite(collect_sayings(self.sayings, self.identity))

    # ---------- 说话习惯（神似）----------
    def _deceased_name(self) -> str:
        """这具分身所承载的人的名字（缅怀/仪式里称呼用）。"""
        return (self.identity or {}).get("name") or "TA"

    def speak_like(self, text, *, particle=True) -> str:
        """给一句回复"上色"，让它更像 TA 本人说的；没配说话习惯则原样返回。"""
        from .mannerisms import apply_style
        if not getattr(self, "mannerisms", None):
            return text
        return apply_style(text, self.mannerisms, particle=particle)

    def speech_habits(self) -> str:
        """自述说话习惯（"你说话有什么习惯"）。"""
        from .mannerisms import describe
        return describe(getattr(self, "mannerisms", None))

    def call_person(self, key) -> str | None:
        """TA 生前怎么称呼这个人（按名字或关系）。"""
        from .mannerisms import address_for
        return address_for(getattr(self, "mannerisms", None), key)

    # ---------- 周年祭 / 纪念仪式 ----------
    def anniversaries_today(self, now=None) -> list:
        from .anniversary import anniversaries_today
        return anniversaries_today((self.memorial or {}).get("dates", {}), now)

    def upcoming_anniversaries(self, within=30, now=None) -> list:
        from .anniversary import days_until
        return days_until((self.memorial or {}).get("dates", {}), now, within)

    def remembrance_ritual(self, name=None, now=None) -> list:
        """走一遍纪念仪式：默认取今天的纪念日；name 可指定某个。返回一句句步骤话。"""
        from .anniversary import anniversaries_today, ritual_steps, who_of
        from .legacy import last_words
        today = anniversaries_today((self.memorial or {}).get("dates", {}), now)
        if name:
            today = [(n, y) for n, y in today if name in n] or [(name, None)]
        if not today:
            return []
        label, years = today[0]
        who = who_of(label) or self._deceased_name()       # "张爸的忌日"→"张爸"，否则用本尊名
        lw = last_words(self.legacy)
        mems = []
        if self.memory is not None:
            mems = [it["text"] for _, it in self.memory.recall(who or label, k=2)]
        return ritual_steps(label, who, last_words=lw[0] if lw else None,
                            memories=mems, years=years)

    # ---------- 遗物 / 信物 ----------
    def _heirloom_items(self) -> list:
        from .heirloom import collect_heirlooms
        return collect_heirlooms(getattr(self, "heirlooms", None), self.legacy)

    def _heirloom_hit(self, text) -> bool:
        """问话里点到了某件信物名（至少两字，避免"表/书"这类单字误触）。"""
        from .heirloom import find_heirloom
        it = find_heirloom(self._heirloom_items(), text)
        return bool(it and len(it["item"]) >= 2)

    def heirloom_story(self, query) -> str:
        """讲一件信物的来历；问"有什么念想"则报清单。"""
        from .heirloom import find_heirloom, list_items, story_of, where_is
        items = self._heirloom_items()
        if not items:
            return ""
        if any(k in (query or "") for k in ("有什么遗物", "什么念想", "哪些遗物", "哪些信物",
                                            "什么信物", "什么东西留", "留了什么")):
            return list_items(items)
        it = find_heirloom(items, query)
        if not it:
            return ""
        s, w = story_of(it), where_is(it)
        return (s + (" " + w if w else "")).strip()

    def bequests_for(self, name) -> str:
        """这个人该得的信物（"有什么留给我"）。"""
        from .heirloom import bequest_to, story_of
        got = bequest_to(self._heirloom_items(), name)
        if not got:
            return ""
        return "有些东西，我想留给你：" + "；".join(story_of(it) for it in got)

    # ---------- 家谱 ----------
    def family_tree_line(self) -> str:
        from .genealogy import build_tree, roster_by_gen
        return roster_by_gen(build_tree(self.family))

    def birthday_reminders(self, within=30, now=None) -> str:
        from .genealogy import birthday_line, build_tree
        return birthday_line(build_tree(self.family), now, within)

    # ---------- 家族病史 / 过敏 ----------
    def health_advice(self) -> str:
        """把家族病史交代给后人（"我身体要注意什么"）。"""
        from .health_history import collect_conditions, health_warning
        return health_warning(collect_conditions(getattr(self, "health", None)))

    def allergy_for(self, name) -> str:
        """某人对什么过敏（做饭/买东西前的一句提醒）。"""
        from .health_history import allergy_line
        return allergy_line(getattr(self, "health", None), name)

    # ---------- 二十四节气 ----------
    def solar_term_today(self, now=None):
        """今天是否正逢某个节气（前后一天）。"""
        from .solar_terms import term_on
        return term_on(now)

    def seasonal_wisdom(self, now=None) -> str:
        """当前时令的一句叮嘱。"""
        from .solar_terms import seasonal_wisdom
        return seasonal_wisdom(now)

    def solar_term_line(self, now=None) -> str:
        """赶上节气当天才说的那句（没赶上返回空，供见面时主动提）。"""
        from .solar_terms import term_on, wisdom
        return wisdom(term_on(now))

    # ---------- 人情往来 ----------
    def favor_ledger(self) -> str:
        if self.favors is None:
            return ""
        return self.favors.describe()

    def favor_remind(self, who) -> str:
        if self.favors is None:
            return ""
        return self.favors.remind(who)

    # ---------- 讲古 / 家庭故事会 ----------
    def _all_stories(self) -> list:
        from .storytelling import collect_stories
        mem = self.memory.items if self.memory is not None else []
        return collect_stories(self.stories, mem)

    def tell_story(self, topic=None, bedtime=False) -> str:
        """挑一个还没讲过的故事娓娓道来；讲完记下，下回换一个。"""
        from .storytelling import pick_story, tell
        stories = self._all_stories()
        if not stories:
            return ""
        s = pick_story(stories, topic=topic, exclude=self._told_stories)
        if not s:
            return ""
        self._told_stories.add(s["story"])
        return tell(s, bedtime=bedtime)

    def story_titles(self) -> list:
        from .storytelling import titles
        return titles(self._all_stories())

    # ---------- 言传身教 ----------
    def teach(self, query) -> str:
        """教手艺或讲道理：先认手艺名，再认"道理/做人"类提问；都不沾就交给上层。"""
        from .teaching import (collect_lessons, collect_skills, find_skill,
                               lesson_on, skill_names, teach_lesson, teach_skill)
        q = query or ""
        if any(k in q for k in ("什么手艺", "什么本事", "会教我什么", "都会啥", "会点啥")):
            names = skill_names(collect_skills(self.teachings))
            return ("我会的有：" + "、".join(names) + "。想学哪样？") if names else ""
        sk = find_skill(collect_skills(self.teachings), q)
        if sk:
            return teach_skill(sk)
        lessons = collect_lessons(self.teachings)
        if lessons and any(k in q for k in ("道理", "为人", "做人", "处世", "教我个",
                                            "教个", "懂得", "的理")):
            return teach_lesson(lesson_on(lessons, q))
        return ""

    def random_teaching(self) -> str:
        """闲下来主动点拨一句道理（供主动场景调用）。"""
        from .teaching import collect_lessons, teach_lesson
        lessons = collect_lessons(self.teachings)
        if not lessons:
            return ""
        import random
        return teach_lesson(random.choice(lessons))

    # ---------- 老伴专属（夫妻之间）----------
    def is_my_spouse(self, name, relation=None) -> bool:
        from .spouse import is_spouse
        return is_spouse(getattr(self, "spouse", None), name, relation)

    def love_story(self) -> str:
        """我们的故事（怎么认识、怎么走到一起）。"""
        from .spouse import love_story
        return love_story(getattr(self, "spouse", None))

    def our_promises_line(self) -> str:
        from .spouse import our_promises
        ps = our_promises(getattr(self, "spouse", None))
        if not ps:
            return ""
        return "咱俩说好的：" + "；".join(ps) + "。这些我都记着。"

    def comfort_spouse(self, utterance="") -> str:
        """老伴流露思念/孤独时，像本人那样温柔接住。"""
        from .spouse import comfort_lonely
        return comfort_lonely(getattr(self, "spouse", None), utterance)

    def soothe_spouse(self, utterance="") -> str:
        """老伴闹脾气/受委屈时，认个软把人哄好。"""
        from .spouse import soothe
        return soothe(getattr(self, "spouse", None), utterance)

    def goodnight_spouse(self, now=None) -> str:
        """夜里给老伴道一声晚安（限傍晚到深夜；非此时段返回空）。"""
        from datetime import datetime
        from .spouse import goodnight
        if not getattr(self, "spouse", None):
            return ""
        hour = (now or datetime.now()).hour
        if hour < 20 and hour > 4:                        # 只在 20:00–次日4:59 道晚安
            return ""
        return goodnight(self.spouse, now)

    def write_love_letter(self, occasion="") -> str:
        """以本人口吻给老伴写一封情书（有大模型则润色，否则用模板）。"""
        from .loveletter import compose_love_letter
        if not getattr(self, "spouse", None):
            return ""
        mems = []
        if self.memory is not None:
            name = self.spouse.get("name", "")
            mems = [it["text"] for _, it in self.memory.recall(name or "老伴", k=3)]
        return compose_love_letter(self.spouse, identity=self.identity,
                                   memories=mems, occasion=occasion, llm=self.llm)

    def nightly_goodnight(self, now=None) -> str:
        """夜里主动给老伴道一声晚安，每晚只道一次（供守护循环调用）。"""
        from datetime import datetime
        g = self.goodnight_spouse(now)
        if not g:
            return ""
        today = (now or datetime.now()).strftime("%Y-%m-%d")
        if self._goodnight_day == today:
            return ""
        self._goodnight_day = today
        return g

    def spouse_ritual_now(self, now=None) -> str:
        """此刻是否到了老夫老妻的日常默契时辰，是则唤一句（同一时辰当天不重复）。"""
        from datetime import datetime
        from .spouse import ritual_now
        if not getattr(self, "spouse", None):
            return ""
        line = ritual_now(self.spouse, now)
        if not line:
            return ""
        key = ((now or datetime.now()).strftime("%Y-%m-%d"), line)
        if key in self._ritual_fired:
            return ""
        self._ritual_fired.add(key)
        return line

    def spouse_anniversary_countdown(self, now=None, within=7) -> str:
        """临近结婚纪念日的提前提醒。"""
        from .spouse import anniversary_reminder
        if not getattr(self, "spouse", None):
            return ""
        return anniversary_reminder(self.spouse, now, within)

    # ---------- 陪伴与守护（present-tense，让分身有人味儿、更主动）----------
    def _weather_hint(self) -> str:
        """从传感器气温粗略给个天气提示（冷/热），用于贴心关照。"""
        t = (getattr(self, "sensors", None) or {}).get("temperature")
        if t is None:
            return ""
        try:
            t = float(t)
        except (TypeError, ValueError):
            return ""
        return "降温" if t <= 10 else ("高温" if t >= 30 else "")

    def companion_checkin(self, now=None) -> str:
        """按时段的主动问候（看天气加一句关照）；同一时段当天只问一次。"""
        from datetime import datetime
        from .companion import checkin, time_of_day
        now = now or datetime.now()
        slot = (now.strftime("%Y-%m-%d"), time_of_day(now))
        if self._companion_slot == slot:
            return ""
        self._companion_slot = slot
        return checkin(now, weather=self._weather_hint(), seed=now.strftime("%H"))

    def wellbeing_nudge(self, now=None) -> str:
        """按时段的健康守护（吃饭/活动/睡觉）；同一时段当天只提醒一次。"""
        from datetime import datetime
        from .companion import time_of_day, wellbeing_nudge
        now = now or datetime.now()
        line = wellbeing_nudge(now)
        if not line:
            return ""
        slot = (now.strftime("%Y-%m-%d"), time_of_day(now))
        if slot in self._wb_fired:
            return ""
        self._wb_fired.add(slot)
        return line

    def present_comfort(self, utterance="", name="") -> str:
        """有人累了/难过了，以"我就在身边"的暖意接住。"""
        from .companion import comfort
        return comfort(utterance, name=name or "")

    # ---------- 打气 / 报喜（替家人惦记、由衷高兴）----------
    def cheer_on(self, utterance, name="") -> str:
        """家人提到要面对的大事，给句鼓励，并记进"惦记本"，事后主动跟进。"""
        from datetime import date
        from .encourage import detect_occasion, encourage
        line = encourage(utterance, name=name)
        if line:
            occ = detect_occasion(utterance)
            if occ and name:
                self._pending_cheer[name] = {"occasion": occ, "day": date.today().isoformat()}
        return line

    def cheer_followup(self, name, now=None) -> str:
        """见到家人，若之前惦记的大事已过了一天，主动问一句结果（问完即销账）。"""
        from datetime import date
        ev = self._pending_cheer.get(name)
        if not ev:
            return ""
        today = (now.date().isoformat() if hasattr(now, "date")
                 else date.today().isoformat())
        if ev["day"] >= today:                          # 还没到第二天，先不催
            return ""
        from .encourage import followup_question
        q = followup_question(ev["occasion"])
        if q:
            self._pending_cheer.pop(name, None)
        return q

    def celebrate_news(self, utterance, name="") -> str:
        """家人报喜，由衷道贺，并把这桩喜事记进生平里程碑。"""
        from .celebrate import celebrate, detect_good_news, milestone_text
        line = celebrate(utterance, name=name)
        if line and self.memory is not None:
            occ = detect_good_news(utterance)
            ms = milestone_text(occ, name)
            if ms:
                try:
                    self.memory.add(ms, source="milestone")
                except Exception:
                    pass
        return line

    # ---------- 脾性 / 幽默 / 唠家常（让分身有血有肉）----------
    def state_preference(self, utterance) -> str:
        """答"你爱吃啥/你讨厌啥"，每次一致。"""
        from .preferences import answer_preference
        return answer_preference(getattr(self, "preferences", None), utterance)

    def opinion(self, thing) -> str:
        """对某样东西表个态。"""
        from .preferences import opinion_on
        return opinion_on(getattr(self, "preferences", None), thing)

    def tell_a_joke(self) -> str:
        """讲个还没讲过的段子。"""
        from .humor import collect_jokes, tell_joke
        j = tell_joke(collect_jokes(getattr(self, "humor", None)), exclude=self._told_jokes)
        if j:
            self._told_jokes.add(j)
        return j

    def banter_back(self, utterance="") -> str:
        from .humor import banter
        return banter(utterance, seed=utterance)

    def chitchat(self, utterance) -> str:
        from .smalltalk import smalltalk_reply
        return smalltalk_reply(utterance, seed=utterance)

    # ---------- 内心活动 / 主见 ----------
    def muse(self, now=None) -> str:
        """闲下来心里冒出的一句（惦记着家人、随时段流动）。"""
        from datetime import datetime
        from .companion import time_of_day
        from .family import members
        from .inner_life import idle_musing
        now = now or datetime.now()
        people = [m["name"] for m in members(self.family)
                  if m.get("name") and m.get("relation") != "本人"][:4]
        return idle_musing(people=people, tod=time_of_day(now), seed=now.strftime("%H%M"))

    def opine_on(self, utterance) -> str:
        """对人生话题给出一贯的看法。"""
        from .opinions import opine
        return opine(getattr(self, "opinions", None), utterance)

    def start_chat(self, now=None) -> str:
        """主动挑个话头唠两句（陪聊、破冷场）。"""
        from datetime import datetime
        from .chat_starters import starter
        from .companion import time_of_day
        from .family import members
        now = now or datetime.now()
        people = [m["name"] for m in members(self.family)
                  if m.get("name") and m.get("relation") != "本人"][:4]
        return starter(seed=now.strftime("%H%M"), people=people, tod=time_of_day(now))

    def drop_proverb(self, utterance) -> str:
        """聊到什么，顺口来句应景的老话。"""
        from .proverbs import proverb_for
        return proverb_for(utterance, seed=utterance)

    def recite_proverbs(self, utterance="") -> str:
        from .proverbs import match_theme, recite
        return recite(match_theme(utterance))

    # ---------- 一起回忆 / 送礼参考 ----------
    def recollect_with(self, person, seed="") -> str:
        """翻出一段和这个人有关的旧时光，说得有温度。"""
        from .memory_lane import recollect
        if self.memory is None or not person:
            return ""
        mems = [it["text"] for _, it in self.memory.recall(person, k=4)]
        return recollect(mems, person=person, seed=seed or person)

    def suggest_gift(self, utterance) -> str:
        """按关系/喜好/场合，给几个送礼主意。"""
        from .family import find_member
        from .gift_ideas import detect_occasion, gift_ideas
        m = find_member(self.family, utterance) if self.family else None
        relation = (m.get("relation") if m else "") or (utterance or "")
        likes = (m.get("likes") if m else None) or []
        if not m and getattr(self, "spouse", None) and any(
                k in (utterance or "") for k in ("老伴", "老婆", "老公", "爱人", "媳妇")):
            relation = self.spouse.get("relation", "老伴")
        return gift_ideas(relation=relation, likes=likes, occasion=detect_occasion(utterance))

    # ---------- 宽慰忧虑 / 小确幸 ----------
    def comfort_worry(self, utterance, name="") -> str:
        from .worries import soothe_worry
        return soothe_worry(utterance, name=name, seed=utterance)

    def record_joy(self, utterance, who="") -> str:
        """记下一件开心事，暖暖回应一句。"""
        if self.joys is None:
            return ""
        self.joys.add(utterance, who=who)
        return self.joys.acknowledge(utterance)

    def reflect_joys(self) -> str:
        return self.joys.reflect() if self.joys is not None else ""

    def joy_evening_prompt(self, now=None) -> str:
        """傍晚主动问一句今天的开心事，每天只问一次（供守护循环调用）。"""
        from datetime import datetime
        from .joys import evening_prompt
        if self.joys is None:
            return ""
        line = evening_prompt(now)
        if not line:
            return ""
        today = (now or datetime.now()).strftime("%Y-%m-%d")
        if self._joy_asked_day == today:
            return ""
        self._joy_asked_day = today
        return line

    # ---------- 守护：用药 / 居家安全 / 就医 ----------
    def take_med(self, name, now=None) -> str:
        if self.medications is None:
            return ""
        m = self.medications.take(name, now)
        if not m:
            return ""
        line = f"好，记下了，{m['name']}吃过了。"
        for nm, stock in self.medications.refill_alerts():
            if nm == m["name"]:
                line += f" 对了，只剩{stock}次的量了，记得去配。"
        return line

    def meds_describe(self) -> str:
        return self.medications.describe() if self.medications is not None else ""

    def safety_prompt(self) -> str:
        from .safety_check import checklist, evening_prompt
        return evening_prompt(checklist(getattr(self, "safety", None)))

    def appointments_describe(self) -> str:
        return self.appointments.describe() if self.appointments is not None else ""

    def proactive_health_reminders(self, now=None) -> list:
        """守护循环用：到点吃药 + 临近就医，按天去重（不重复念）。"""
        from datetime import datetime
        now = now or datetime.now()
        day = now.strftime("%Y-%m-%d")
        out = []
        if self.medications is not None:
            for line in self.medications.reminders(now):
                key = (day, line)
                if key not in self._med_fired:
                    self._med_fired.add(key)
                    out.append(line)
        if self.appointments is not None:
            for line in self.appointments.reminders(now):
                key = (day, line)
                if key not in self._appt_fired:
                    self._appt_fired.add(key)
                    out.append(line)
        return out

    def spouse_anniversary(self, now=None) -> str:
        from .spouse import anniversary_words
        return anniversary_words(getattr(self, "spouse", None), now)

    def spouse_care_today(self, now=None) -> list:
        """对老伴饱含爱意的唠叨；当天只唠叨一次（去重）。"""
        from datetime import date
        from .spouse import care_words
        if not getattr(self, "spouse", None):
            return []
        today = (now.date() if hasattr(now, "date") else date.today()).isoformat()
        if self._spouse_nag_day == today:
            return []
        self._spouse_nag_day = today
        return care_words(self.spouse, now)

    def spouse_greeting(self, now=None) -> str:
        """见到老伴的专属问候：昵称 + 纪念日 + 一句牵挂（去重唠叨）。供 greet 调用。"""
        from .spouse import call_name
        if not getattr(self, "spouse", None):
            return ""
        parts = [f"{call_name(self.spouse)}，你来啦。"]
        anni = self.spouse_anniversary(now)
        if anni:
            parts.append(anni)
        parts += self.spouse_care_today(now)
        return " ".join(parts)

    def kinship(self, text) -> str:
        """算亲戚称呼："我爸的弟弟" → "该叫叔叔"。"""
        from .kinship import call_what
        return call_what(text)

    def festival_today(self, now=None) -> str:
        from .festival import today_line
        return today_line(now)

    def festival_info(self, text) -> str:
        """报某个节的祝福与讲究（"端午有什么讲究"）。"""
        from .festival import _INFO, customs, greeting
        t = text or ""
        for name in _INFO:
            core = name.rstrip("节")
            if name in t or (len(core) >= 2 and core in t):
                cu = customs(name)
                return greeting(name) + (f" 老讲究：{cu}" if cu else "")
        return ""

    # ---------- 社交记忆 / 心愿目标 ----------
    def relation_with(self, name) -> str:
        s = getattr(self, "social", None)
        return s.describe(name) if s is not None else ""

    def long_unseen(self) -> list:
        """太久没见的人，提一句。"""
        s = getattr(self, "social", None)
        if s is None:
            return []
        return [f"好久没见{n}了（{d}天），抽空联系一下？" for n, d in s.cooled()]

    def set_goal(self, text) -> str:
        g = getattr(self, "goals", None)
        if g is None:
            return ""
        goal = g.add(text)
        return f"好，记下了这个心愿：{goal['text']}。我帮你盯着。" if goal else ""

    def goals_summary(self) -> str:
        g = getattr(self, "goals", None)
        return g.summary() if g is not None else ""

    def complete_goal(self, query) -> str:
        g = getattr(self, "goals", None)
        if g is None:
            return ""
        done = g.complete(query)
        return f"太好了，「{done['text']}」做到了！" if done else ""

    # ---------- 采买清单 ----------
    def shop_add(self, name, qty=None) -> str:
        s = getattr(self, "shopping", None)
        if s is None:
            return ""
        it = s.add(name, qty)
        return f"好，加到采买清单了：{it['name']}" + (f"×{it['qty']}" if it.get('qty') else "") if it else ""

    def shop_done(self, name) -> str:
        s = getattr(self, "shopping", None)
        if s is None:
            return ""
        it = s.check_off(name)
        return f"{it['name']} 划掉了。" if it else f"清单里没找到「{name}」。"

    def shop_list(self) -> str:
        s = getattr(self, "shopping", None)
        return s.describe() if s is not None else ""

    # ---------- 哀伤阶段陪伴 ----------
    def _passed_on_date(self):
        """从配置里找"离开的日子"（legacy.passed_on 或 memorial.dates 里含忌日/过世的项）。"""
        po = (self.legacy or {}).get("passed_on")
        if po:
            return po
        for label, d in ((self.memorial or {}).get("dates", {}) or {}).items():
            if any(k in str(label) for k in ("忌日", "过世", "走了", "离开", "逝")):
                return d
        return None

    def grief_stage_line(self, who_name=None, now=None) -> str:
        from datetime import datetime as _dt
        from .comfort_stages import comfort_by_stage, days_between
        days = days_between(self._passed_on_date(), now or _dt.now())
        return comfort_by_stage(days, who_name)

    # ---------- 触景生情 / 感恩与遗憾 ----------
    def reminisce_about(self, cue) -> str:
        """顺着一个由头，回想相关记忆与当时的情绪，说一段带温度的回想。"""
        from .reminisce import reminisce
        from .style import apply_style
        recalled = self._recall(cue or "", k=2)
        mems = [it["text"] for _, it in recalled]
        emotion = None
        if recalled:
            emotion = (recalled[0][1].get("emotion") or "").strip() or None
        return apply_style(reminisce(cue, mems, emotion), self.identity)

    def reflect_gratitude(self) -> str:
        """回望一生，说出最感念的与放不下的。"""
        from .gratitude import reflect
        from .style import apply_style
        return apply_style(reflect(self.memory.items), self.identity)

    # ---------- 多人合一：一座数字宅里住着不止一个人 ----------
    def family_roster(self) -> str:
        from .family import roster_line
        return roster_line(self.family)

    def find_family_members(self, query) -> list:
        """从一句话里认出提到的家人（按名字或称呼），按出现顺序返回、去重。"""
        from .family import members
        q = str(query or "")
        out, seen = [], set()
        for m in members(self.family):
            name, rel = m.get("name", ""), m.get("relation", "")
            if ((name and name in q) or (rel and rel in q)) and name not in seen:
                seen.add(name)
                out.append(m)
        return out

    def let_them_talk(self, query) -> str:
        """让被点到的两位（或更多）家人，就某话题各用各的口吻聊几句。"""
        from .converse import extract_topic, family_dialogue
        ms = self.find_family_members(query)
        if len(ms) < 2:
            return ""
        turns = family_dialogue(ms, extract_topic(query, ms), llm=self.llm)
        return "\n".join(f"{t['speaker']}：{t['text']}" for t in turns)

    def member_memories(self, name, limit: int = 8) -> list:
        """某位家人的专属记忆文本（按 member:<名字> 标签筛）。"""
        tag = f"member:{name}"
        out = [it.get("text", "") for it in self.memory.items if tag in (it.get("tags") or [])]
        return [t for t in out if t][:limit]

    def build_family_book(self, topic="家常") -> str:
        """把全家编成一本自包含 HTML 家族册：每位一页 + 一段对谈。"""
        from .book import dialogue_section, family_book_html, member_section
        from .converse import family_dialogue
        from .family import members, roster_line
        ms = members(self.family)
        secs = [member_section(m, self.member_memories(m["name"])) for m in ms]
        dlg = ""
        if len(ms) >= 2:
            turns = family_dialogue(ms[:2], topic, llm=self.llm)
            dlg = dialogue_section(turns)
        title = (self.identity.get("name", "") + "家") if self.identity.get("name") else "我们家"
        return family_book_html(title, secs, family_line=roster_line(self.family), dialogue=dlg)

    def become(self, query) -> str:
        """把某位家人"叫出来"：热切换到 TA 本人的口吻继续对话，并以 TA 的口气打个招呼。"""
        from .family import find_member, member_identity
        from .persona import Persona
        from .style import apply_style
        m = find_member(self.family, query)
        if not m:
            return ""
        if self._home_identity is None:                # 首次切换前，记下本尊以便还原
            self._home_identity, self._home_persona = self.identity, self.persona
        self.identity = member_identity(m, self.family)
        self.persona = Persona(self.identity)
        self.active_member = self.identity["name"]
        hi = m.get("greeting") or f"我是{self.active_member}，来啦，想说点啥？"
        return apply_style(hi, self.identity)

    def restore_home(self) -> str:
        """把本尊请回来（结束某位家人的'出场'）。"""
        if self._home_identity is not None:
            self.identity, self.persona = self._home_identity, self._home_persona
            self._home_identity = self._home_persona = None
        self.active_member = None
        return f"好，我又是{self.identity.get('name', '我')}了。"

    def remember_photo(self, people=None, when=None, caption=None, place=None) -> str:
        """把一张照片记下来：拼成带日期的记忆，并把照片里登记在册的家人归到 TA 名下。"""
        from .photo import member_tags, photo_memory
        text = photo_memory(people, when=when, caption=caption, place=place)
        tags = ["photo"] + [p for p in (people or []) if p] + member_tags(people, self.family)
        self.memory.add(text, source="photo", tags=tags, when=when)
        return text

    # ---------- 编年生平 + 嘱托（数字遗产）----------
    def life_chronicle(self) -> str:
        from .legacy import chronicle
        from .style import apply_style
        return apply_style(chronicle(self.memory.items), self.identity)

    def deliver_last_words(self) -> str:
        from .legacy import last_words
        from .style import apply_style
        lw = last_words(self.legacy)
        if not lw:
            return ""
        return apply_style("有几句话，我一直想留给你：" + " ".join(f"「{w}」" for w in lw), self.identity)

    def deliver_precepts(self) -> str:
        from .legacy import precepts
        from .style import apply_style
        ps = precepts(self.legacy)
        if not ps:
            return ""
        return apply_style("咱们家的老规矩，我念给你听：" + " ".join(f"「{p}」" for p in ps), self.identity)

    def _fallback_greet(self, who: dict) -> str:
        name = who["name"]
        if not who.get("known"):
            return "你好，请问您是哪位？"
        if not who.get("obey"):
            return f"（看了一眼{name}，没有说话。）"
        # 神似：若 TA 生前对这人有专属称呼（如管孙子叫"乖乖"），就用 TA 的叫法
        call = self.call_person(name) or self.call_person(who.get("relation")) or name
        if who.get("guard"):
            return self.speak_like(f"{call}回来啦！我一直在等你呢。")
        if who.get("trust") == "family":
            return self.speak_like(f"{call}，你来啦！")
        return self.speak_like(f"嘿，{call}，好久不见！")

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
                if getattr(self, "worldmodel", None) is not None:   # 学到的沉淀成信念（知识在累积）
                    self.worldmodel.reinforce(f"learned:{q['term']}", f"我了解到「{q['term']}」是怎么回事")
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
        extra = []
        router = getattr(self, "llm_router", None)
        if router is not None:                       # 多模型：让不同模型各出一票（异质认知多样性）
            for m in router.panel():
                if not getattr(m, "available", False):
                    continue
                try:
                    ans = m.chat("只回一行：先说 会/悬/观望，再加一句简短理由。", question)
                    lean = 1 if "会" in ans else (-1 if ("悬" in ans or "不" in ans) else 0)
                    extra.append((f"模型·{m.model}", lean, ans[:18]))
                except Exception:
                    pass
        fc = forecast(question, llm=self.llm, extra=extra)
        if fc.get("diversity", 0) >= 0.5 and getattr(self, "curiosity", None) is not None:
            q = f"「{(question or '')[:18]}」这事我心里几种思路打架，挺想弄明白。"
            self.curiosity.add((question or "?")[:12] or "?", q, priority=0.9)
        return fc["text"]

    def federated_forecast(self, question) -> str:
        """预测联邦：把外部智能体也拉进小会当独立思维节点，集思广益再聚合。"""
        from .swarm import forecast
        extra = []
        if self.hub is not None:
            for name in self.hub.names():
                res = self.hub.dispatch(name, "forecast", question=question)
                if res.get("ok"):
                    txt = str(res.get("result", ""))
                    lean = 1 if "会" in txt else (-1 if ("悬" in txt or "不" in txt) else 0)
                    extra.append((f"外脑·{name}", lean, txt[:18]))
        return forecast(question, llm=self.llm, extra=extra)["text"]

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
        from .style import apply_style
        from .values import deliberate as _deliberate
        return apply_style(_deliberate(text, values=self.values,
                                       guarded=self.authority.guarded_people(), llm=self.llm), self.identity)

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
        """强度感知检索：相关性 × (0.4 + 0.6×记忆强度)，淡忘的更难被想起。

        若此刻"叫出"了某位家人（多人合一），TA 自己的记忆会被额外加权——更像 TA 本人在回想。
        """
        from .forgetting import strength
        cand = self.memory.recall(text, k=k * 3)
        boost_tag = f"member:{self.active_member}" if getattr(self, "active_member", None) else None

        def weight(si):
            s, it = si
            base = s * (0.4 + 0.6 * strength(it, now))
            if boost_tag and boost_tag in (it.get("tags") or []):
                base *= 1.8           # 当某位家人"在场"，TA 自己的记忆更容易被想起
            return -base

        return sorted(cand, key=weight)[:k]

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
        from .style import apply_style
        return apply_style(compose_self_narrative(
            name, core_people=core, mood_desc=mood_desc, insight=refl[0] if refl else None,
            cherished=cherished, dream=dream, traits=traits, llm=self.llm), self.identity)

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
        if any(k in u for k in _CARE_KW):
            return self.care_briefing(name=who["name"] if who.get("known") else None)
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
