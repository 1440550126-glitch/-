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
_DIAG_KW = ("自检", "系统状态", "运行状况", "诊断", "各系统", "系统自检", "系统体检", "diagnostic", "status")
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
                 opinions=None, joys=None, habits_book=None,
                 contacts=None, ledger=None, bedtime=None,
                 music=None, plants=None, touch=None, understanding=None,
                 messages=None, vitals=None, board=None, growth=None,
                 pets=None, reminders=None, countdown=None, todo=None,
                 belongings=None, poetry=None) -> None:
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
        self.dialogue: deque = deque(maxlen=6)                    # 这一席话的近几句（对话连贯·像人）
        self._threads: dict = {}                                  # 你上次提到没完的事（跨天记挂）
        self._inferred_day = None                                 # 当天是否已主动说过推断（去重）
        self._last_body = ""                                      # 此刻的体态（注入灵魂的身体·供网页展示）
        self._last_face = ""                                      # 此刻的神情（脸+灯色·供网页展示）
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
        self.habits_book = habits_book                            # 习惯养成陪练（戒烟/早睡/锻炼打卡）
        self._habit_reminded_day = None                           # 当天是否已催过打卡（去重）
        self.contacts = contacts                                  # 重要联系人电话本（要紧时找得到）
        self.ledger = ledger                                      # 家庭账本（随口记账、月底算清）
        self.bedtime = bedtime or {}                              # 睡前故事库（给孙辈哄睡）
        self._told_bedtime: set = set()                           # 已讲过的睡前故事（轮换）
        self.music = music or {}                                  # 老歌：爱唱的歌 / 按心情点歌
        self.plants = plants                                      # 养花：浇水提醒
        self._plant_reminded_day = None                           # 当天是否已提醒浇水（去重）
        self.touch = touch                                        # 常联系：别让亲情淡了
        self._touch_reminded_day = None                           # 当天是否已提醒联系（去重）
        self.understanding = understanding                        # 我眼里的你：对每个人渐渐形成的理解
        self._reached: set = set()                                # 当天已主动牵挂过的人（去重）
        self.messages = messages                                  # 捎话：替家人带话，等人来了主动捎到
        self.vitals = vitals                                      # 体征记录（血压/血糖/体重，看趋势、异常提醒）
        self.board = board                                        # 家庭共享·分工板（谁买菜/谁接孩子）
        self._chore_reminded: set = set()                         # 当天已提醒过的分工（去重）
        self.growth = growth                                      # 成长记录（孙辈的成长点滴）
        self.pets = pets                                          # 养宠：喂食/遛弯提醒
        self._pet_reminded: set = set()                           # 当天已提醒过的喂宠（去重）
        self.reminders = reminders                                # 随口提醒（"提醒我三点吃药"）
        self.countdown = countdown                                # 倒计时（离过年/退休/高考还有几天）
        self.todo = todo                                          # 个人待办清单（自己的一张小清单）
        self.belongings = belongings                              # 找东西（钥匙/老花镜/存折搁哪了）
        self.poetry = poetry                                      # 背诗：跟孙辈对诗/整首背
        self._noticed: set = set()                                # 已点破过的"门道"（当天去重）
        self._told_riddles: set = set()                           # 出过的谜语/急转弯（轮换）
        self._pending_riddle = None                               # 正等你猜的谜（题, 答案）
        self._game_mode = None                                    # 正在玩的游戏（如"接龙"）
        self._feihua_used: dict = {}                              # 飞花令各字已对过的句子（不重样）
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
        self.mouth = None            # "嘴"：语音模式下挂上它，主动说的话会边说边动（说动合一）
        self._festival_nudged: set = set()  # 当天已张罗过的节日（按日期+节日去重）

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

        # --- 注入灵魂的身体：有人说话，转头看向 TA（专注地听）---
        if who.get("known") and action is None:
            from .embodiment import attend
            attend(getattr(self, "robot", None), who.get("name"))

        # --- 社交记忆：跟"认识的人"每打一次交道，更新这段关系的亲疏冷暖 ---
        if who.get("known") and getattr(self, "social", None) is not None:
            try:
                emo = self.emotions.mood()[0] if getattr(self, "emotions", None) else None
                topic = (utterance or "").strip()[:10] or None
                self.social.note(who["name"], emotion=emo, topic=topic)
            except Exception:
                pass

        # --- 对话连贯：把这句存进"这一席话"的缓冲，回应时能接着前面的话头（像人）---
        if who.get("known") and action is None and getattr(self, "dialogue", None) is not None:
            self.dialogue.append((utterance or "").strip())

        # --- 跨天记挂：你提到要去办的/担心的/不舒服的，记个尾巴，下次见你问一句 ---
        if who.get("obey") and action is None:
            self._note_thread(who.get("name"), utterance)

        # --- 我眼里的你：把这次互动沉淀进对TA的理解（越处越懂）---
        if who.get("known") and getattr(self, "understanding", None) is not None:
            try:
                from .annotate import classify_emotion
                emo2 = classify_emotion(utterance).get("label")
                self.understanding.observe(who["name"], utterance,
                                           emotion=None if emo2 == "平静" else emo2)
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
        from .lost_help import senses_lost as _senses_lost
        if action is None and who.get("obey") and not _senses_lost(utterance):
            sret = self._scene_route(speaker_name, utterance)
            if sret is not None:
                # 既开关灯、也当那个门口的人：离家/回家时把暖话缀在前头
                from .farewell import is_back, is_leaving, send_off, welcome_back
                u = utterance or ""
                warm = (send_off(self._addr(who), seed=u) if is_leaving(u)
                        else welcome_back(self._addr(who), seed=u) if is_back(u) else "")
                if warm:
                    sret = f"{warm} {sret}"
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

        # --- 门口的人：出门相送 / 回家迎接（情感层，设备场景没接住时） ---
        if action is None and who.get("obey"):
            from .farewell import is_back, is_leaving, send_off, welcome_back
            u = utterance or ""
            ftxt = ""
            if is_leaving(u):
                ftxt = send_off(self._addr(who), seed=u)
            elif is_back(u):
                ftxt = welcome_back(self._addr(who), seed=u)
            if ftxt:
                result["reply"] = ftxt
                if self.social is not None:
                    self.social.note(who.get("name"), emotion="爱", topic="迎送")
                self._log_journal(who, u, ftxt, "farewell")
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

        # --- 防诈骗（守护·高优先）：听出骗钱套路就立刻拦一句、给三条当下能做的 ---
        if action is None and who.get("obey"):
            from . import antifraud as af
            if af.smells_like_scam(utterance) or af.is_fraud_question(utterance):
                txt = self.antifraud_handle(utterance, who)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="惧", topic="防诈")
                    self._log_journal(who, utterance, txt, "antifraud")
                    return result

        # --- 告别与释怀：来想念/告别的人说出不舍，以本人口吻温柔回应、给一份释怀（数字魂的本意）---
        if action is None and who.get("obey"):
            from .condolence import console, senses_mourning
            if senses_mourning(utterance):
                txt = console(utterance, name=who.get("name", ""),
                              relation=who.get("relation", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="释怀")
                    self._log_journal(who, utterance, txt, "condolence")
                    return result

        # --- 托住（最高优先）：接住最重的那句"不想活了"，稳稳托住、引向身边的人与帮助 ---
        if action is None and who.get("obey"):
            from .gentle_insist import senses_despair
            if senses_despair(utterance):
                txt = self.hold_despair(who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="托住")
                    self._log_journal(who, utterance, txt, "hold")
                    return result

        # --- 应急（最高优先）：摔了/胸口疼/喘不上气/救命，第一时间稳住并给指引 ---
        if action is None and who.get("obey"):
            from .emergency import senses_emergency
            if senses_emergency(utterance):
                txt = self.emergency_help(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "emergency")
                    return result

        # --- 迷路 / 走失（守护·高优先）：在外头找不到家，稳住并一步步教 TA 怎么办 ---
        if action is None and who.get("obey"):
            from .lost_help import senses_lost
            if senses_lost(utterance):
                txt = self.lost_help_handle(utterance, who)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="惧", topic="迷路")
                    self._log_journal(who, utterance, txt, "lost_help")
                    return result

        # --- 游戏进行中：先看这句是不是在接龙 / 报谜底（仅当真在玩时才接管）---
        if action is None and who.get("obey") and (self._pending_riddle or self._game_mode):
            g = self.try_resolve_game(utterance)
            if g:
                result["reply"] = g
                self._log_journal(who, utterance, g, "game")
                return result

        # --- 安抚惊惧（高优先）：怕黑/噩梦/独自在家，立刻稳住给安全感 ---
        if action is None and who.get("obey"):
            from .comfort_fear import senses_fear
            if senses_fear(utterance):
                txt = self.reassure_fear(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="惧", topic="安抚")
                    self._log_journal(who, utterance, txt, "comfort_fear")
                    return result

        # --- 稳住心神：心慌/坐立不安，带个呼吸或着地练习把人从慌乱里拉回来 ---
        if action is None and who.get("obey"):
            from .comfort_anxiety import calm, senses_anxiety
            if senses_anxiety(utterance):
                txt = calm(utterance, name=who.get("name", ""), seed=utterance)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="惧", topic="稳心")
                    self._log_journal(who, utterance, txt, "comfort_anxiety")
                    return result

        # --- 哄孩子（"孩子一直哭怎么办" / "娃不吃饭"）：温和带娃，先接情绪再想招 ---
        if action is None and who.get("obey"):
            from .soothe_child import is_child_soothing, soothe
            if is_child_soothing(utterance):
                txt = soothe(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "soothe_child")
                    return result

        # --- 哄消气：闹脾气/受委屈/拌嘴时，不犟嘴，先认领情绪、给台阶、拉回暖处 ---
        if action is None and who.get("obey"):
            from . import coax as _coax
            if _coax.is_upset(utterance) or _coax.is_make_up_cue(utterance):
                txt = self.coax_handle(utterance, who)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="哀", topic="哄")
                    self._log_journal(who, utterance, txt, "coax")
                    return result

        # --- 助眠：睡不着/失眠，不讲故事不说教，轻声陪你慢下来（present-tense） ---
        if action is None and who.get("obey"):
            from .sleep_aid import senses_sleepless
            if senses_sleepless(utterance):
                txt = self.sleep_aid_handle(utterance, who)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="哀", topic="助眠")
                    self._log_journal(who, utterance, txt, "sleep_aid")
                    return result

        # --- 该犟就犟：你说不吃药/不看病/太拼，它拦着劝着，因为在乎（不顺着你害你）---
        if action is None and who.get("obey"):
            from .gentle_insist import senses_self_neglect
            if senses_self_neglect(utterance):
                txt = self.insist_care(utterance, who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="劝")
                    self._log_journal(who, utterance, txt, "insist")
                    return result

        # --- 老来的宽慰（高优先）：怕成累赘/没用了/记性差，接住并给一句挺直腰板的暖 ---
        if action is None and who.get("obey"):
            from .dignity import reassure_dignity, senses_aging_worry
            if senses_aging_worry(utterance):
                txt = reassure_dignity(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="宽慰")
                    self._log_journal(who, utterance, txt, "dignity")
                    return result

        # --- 和事佬：家人闹别扭，不偏帮、顺顺气、搭个台阶 ---
        if action is None and who.get("obey"):
            from .mediate import senses_conflict
            if senses_conflict(utterance):
                txt = self.mediate_conflict(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "mediate")
                    return result

        # --- 报喜：家人有了好消息，由衷替TA高兴（并记进里程碑）---
        # --- 看天识天（"燕子低飞是要下雨吗" / "蚂蚁搬家"）：先于报喜，免得把"蚂蚁搬家"当乔迁 ---
        if action is None and who.get("obey"):
            from . import weather_lore as _wl
            _wcfg = self.identity if isinstance(self.identity, dict) else None
            if _wl.is_weather_lore_query(utterance, _wcfg):
                txt = _wl.lore_for(utterance, _wcfg) or _wl.random_lore(
                    seed=utterance or "", config=_wcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "weather_lore")
                    return result

        # --- 祝福语 / 贺词（"结婚说句祝福语" / "拜年话咋说"）：要的就是句体面话，先于报喜/寄语 ---
        if action is None and who.get("obey"):
            from .blessings import is_blessing_request
            if is_blessing_request(utterance):
                txt = self.blessing_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "blessing")
                    return result

        # --- 人情礼俗（"喝喜酒有啥讲究" / "送礼忌讳" / "奔丧要注意啥"）：场面上的分寸 ---
        if action is None and who.get("obey"):
            from . import etiquette as _et
            if _et.is_etiquette_query(utterance):
                u2 = utterance or ""
                if any(k in u2 for k in ("送礼忌讳", "送礼禁忌", "什么忌讳", "送礼避讳",
                                         "送礼讲究")):
                    txt = _et.gift_taboos()
                else:
                    txt = _et.etiquette_for(_et.detect_occasion(u2)) or _et.gift_taboos()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "etiquette")
                    return result

        # --- 人生节点寄语（高考/成家/退休/创业…）：长辈那句过来人的话，比泛泛道喜更暖 ---
        if action is None and who.get("obey"):
            from .life_milestones import detect_milestone
            _mcfg = self.identity if isinstance(self.identity, dict) else None
            if detect_milestone(utterance, _mcfg):
                txt = self.milestone_handle(utterance, who)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="寄语")
                    self._log_journal(who, utterance, txt, "milestone")
                    return result

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
            from .home_cooking import is_cooking_howto as _is_cook
            from .joys import is_sharing_joy
            # "可乐鸡翅咋做"里的"乐"不是开心，是道菜——别记成小确幸
            if is_sharing_joy(utterance) and not _is_cook(utterance):
                txt = self.record_joy(utterance, who=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="喜", topic="开心事")
                    self._log_journal(who, utterance, txt, "joy")
                    return result

        # --- 放下旧怨/悔：心里搁着没原谅、对不起、当年的悔，劝你松开、趁来得及去和好 ---
        if action is None and who.get("obey"):
            from .reconcile import senses_regret, soothe_regret
            if senses_regret(utterance):
                txt = soothe_regret(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="哀", topic="放下")
                    self._log_journal(who, utterance, txt, "reconcile")
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

        # --- 起名取名（"帮孩子起个名字" / "睿字什么寓意"）：家里添丁的大事，先于软聊路由 ---
        if action is None and who.get("obey"):
            from . import naming as _nm
            _nmcfg = self.identity if isinstance(self.identity, dict) else None
            _nm_ask = _nm.explain_request(utterance)
            if _nm_ask:
                txt = f"「{_nm_ask}」起名取意：{_nm.explain_char(_nm_ask, _nmcfg)}。给孩子一生的好彩头。"
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "naming")
                return result
            if _nm.is_naming_query(utterance, _nmcfg):
                txt = self.naming_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "naming")
                    return result

        # --- 名言金句（"来句名言" / "关于坚持的名言" / "座右铭"）：有出处的名句，先于夸夸/打气 ---
        #     放在软聊路由之前：免得"关于坚持的名言"里的"坚持"被当成夸点或打气场合。
        if action is None and who.get("obey"):
            from . import quotes as _q
            _qcfg = self.identity if isinstance(self.identity, dict) else None
            if _q.is_quote_query(utterance, _qcfg):
                theme = _q.find_theme(utterance, _qcfg)
                if theme and any(k in (utterance or "") for k in ("几句", "多来", "几条", "写贺卡", "勉励")):
                    txt = "送你几句——" + _q.several(theme, n=3, seed=utterance, config=_qcfg)
                else:
                    txt = _q.a_quote(theme, seed=utterance, config=_qcfg)
                    if theme:
                        txt = f"说到{theme}：{txt}"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "quotes")
                    return result

        # --- 夸夸/肯定：明着求夸，或说起了值得肯定的事（孝顺/努力/善良…），走心地夸 ---
        if action is None and who.get("obey"):
            from .praise import detect_trait, is_praise_request
            if is_praise_request(utterance) or detect_trait(utterance):
                txt = self.give_praise(utterance, name=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="喜", topic="肯定")
                    self._log_journal(who, utterance, txt, "praise")
                    return result

        # --- 成长记录：孙辈的成长点滴，记一笔；问"X长大的事"则一桩桩讲 ---
        if action is None and who.get("obey") and self.growth is not None:
            ug = utterance or ""
            if any(k in ug for k in ("的成长", "长大的事", "成长记录", "成长点滴")) and self._child_in(ug):
                txt = self.growth_recall(self._child_in(ug))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, ug, txt, "growth_recall")
                    return result
            from .growth_log import detect_milestone
            if detect_milestone(ug) and self._child_in(ug):
                txt = self.record_growth(ug)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="喜", topic="成长")
                    self._log_journal(who, ug, txt, "growth")
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

        # --- 解梦（"梦见蛇是什么意思"）：按民间说法给个宽心吉利的解释 ---
        if action is None and who.get("obey"):
            from .dream_interpret import interpret, is_dream_query
            if is_dream_query(utterance):
                txt = interpret(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "dream_interpret")
                    return result

        # --- 成语故事（"守株待兔的故事" / "亡羊补牢什么意思"）---
        if action is None and who.get("obey"):
            from .idiom_story import find as _idiom_find
            from .idiom_story import is_idiom_query, tell
            if is_idiom_query(utterance):
                txt = tell(_idiom_find(utterance))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "idiom_story")
                    return result

        # --- 成语词典（"雪中送炭什么意思" / "解释一下卧薪尝胆"）：没典故的成语查释义 ---
        if action is None and who.get("obey"):
            from . import idioms_dict as _idict
            _idcfg = self.identity if isinstance(self.identity, dict) else None
            if _idict.is_idiom_lookup(utterance, _idcfg):
                txt = _idict.explain(utterance, _idcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "idioms_dict")
                    return result

        # --- 对对子（"天对什么" / "来对个对子"）---
        if action is None and who.get("obey"):
            from .couplets import is_couplet, respond
            if is_couplet(utterance):
                txt = respond(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "couplet")
                    return result

        # --- 名山大川（"五岳是哪五座" / "泰山在哪" / "故宫介绍"）：祖国大好河山 ---
        if action is None and who.get("obey"):
            from . import landmarks as _lm
            _lmcfg = self.identity if isinstance(self.identity, dict) else None
            if _lm.is_landmark_query(utterance, _lmcfg):
                u2 = utterance or ""
                if "五岳" in u2 and not _lm.find_landmark(u2, _lmcfg):
                    txt = _lm.five_mountains()
                elif "四大名楼" in u2 or ("名楼" in u2 and not _lm.find_landmark(u2)):
                    txt = "江南三大名楼是黄鹤楼、岳阳楼、滕王阁（加鹳雀楼并称四大名楼）。"
                else:
                    txt = _lm.about(u2, _lmcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "landmarks")
                    return result

        # --- 八大菜系（"川菜有什么名菜" / "八大菜系是哪八个"）---
        if action is None and who.get("obey"):
            from . import cuisines as _cui
            _cuicfg = self.identity if isinstance(self.identity, dict) else None
            if _cui.is_cuisine_query(utterance, _cuicfg):
                u2 = utterance or ""
                if "菜系" in u2 and not _cui.find_cuisine(u2, _cuicfg):
                    txt = _cui.eight_cuisines()
                else:
                    txt = _cui.about(u2, _cuicfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "cuisines")
                    return result

        # --- 吉祥寓意（"蝙蝠是什么寓意" / "为什么贴鱼"）：好彩头的讲究 ---
        if action is None and who.get("obey"):
            from . import auspicious as _au
            _aucfg = self.identity if isinstance(self.identity, dict) else None
            if _au.is_auspicious_query(utterance, _aucfg):
                txt = _au.meaning_of(utterance, _aucfg)
                if not txt and any(k in (utterance or "") for k in ("吉祥图案", "吉祥寓意", "好彩头")):
                    txt = "讨彩头常用这些：" + "、".join(_au.symbols(_aucfg)[:8]) + "……想知道哪个的寓意跟我说。"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "auspicious")
                    return result

        # --- 传统手工艺（"剪纸怎么做" / "景泰蓝是什么" / "非遗有哪些"）---
        if action is None and who.get("obey"):
            from . import crafts as _cf
            _cfcfg = self.identity if isinstance(self.identity, dict) else None
            if _cf.is_craft_query(utterance, _cfcfg):
                txt = _cf.about(utterance, _cfcfg)
                if not txt and any(k in (utterance or "") for k in ("手工艺", "非遗", "传统工艺", "老手艺")):
                    txt = "老手艺有不少：" + "、".join(_cf.crafts(_cfcfg)[:8]) + "……想了解哪样跟我说。"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "crafts")
                    return result

        # --- 书法字体（"楷书是什么样" / "楷书四大家" / "想练毛笔字"）---
        if action is None and who.get("obey"):
            from . import calligraphy as _cal
            _calcfg = self.identity if isinstance(self.identity, dict) else None
            if _cal.is_calligraphy_query(utterance, _calcfg):
                u2 = utterance or ""
                if "四大家" in u2:
                    txt = _cal.four_masters()
                else:
                    txt = _cal.about(u2, _calcfg)
                    if not txt and any(k in u2 for k in ("书法", "字体", "练字", "毛笔字")):
                        txt = "书法五体：" + "、".join(_cal.scripts(_calcfg)[:5]) + "。想了解哪种跟我说。"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "calligraphy")
                    return result

        # --- 中国传统色（"天青是什么颜色" / "黛色是啥"）：又雅又美 ---
        if action is None and who.get("obey"):
            from . import colors_cn as _cc
            _cccfg = self.identity if isinstance(self.identity, dict) else None
            if _cc.is_color_query(utterance, _cccfg):
                txt = _cc.about(utterance, _cccfg)
                if not txt and any(k in (utterance or "") for k in ("传统色", "中国色", "古代颜色")):
                    txt = "中国传统色有不少美名：" + "、".join(_cc.colors(_cccfg)[:8]) + "……想知道哪个跟我说。"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "colors_cn")
                    return result

        # --- 认民族乐器（"二胡是什么乐器" / "琵琶名曲"）---
        if action is None and who.get("obey"):
            from . import instruments as _in
            _incfg = self.identity if isinstance(self.identity, dict) else None
            if _in.is_instrument_query(utterance, _incfg):
                txt = _in.about(utterance, _incfg)
                if not txt and any(k in (utterance or "") for k in ("民族乐器", "传统乐器", "国乐")):
                    txt = "民族乐器有不少：" + "、".join(_in.instruments(_incfg)[:8]) + "……想了解哪个跟我说。"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "instruments")
                    return result

        # --- 神话传说（"盘古开天的故事" / "讲个神话"）---
        if action is None and who.get("obey"):
            from . import myths as _my
            _mycfg = self.identity if isinstance(self.identity, dict) else None
            if _my.is_myth_query(utterance, _mycfg):
                txt = _my.about(utterance, _mycfg)
                if not txt and any(k in (utterance or "") for k in ("神话", "传说")):
                    import random as _r
                    pool = _my.myths(_mycfg)
                    txt = _my.about(pool[_r.Random((utterance or "")).randint(0, len(pool) - 1)], _mycfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "myths")
                    return result

        # --- 古典名著（"四大名著是哪四部" / "西游记主要人物"）---
        if action is None and who.get("obey"):
            from . import classic_books as _cb
            if _cb.is_book_query(utterance):
                u2 = utterance or ""
                if "四大名著" in u2 and not _cb.find_book(u2):
                    txt = _cb.four_classics()
                elif any(k in u2 for k in ("主要人物", "里有谁", "有谁", "人物")):
                    txt = _cb.characters(u2) or _cb.about(u2)
                else:
                    txt = _cb.about(u2) or _cb.four_classics()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "classic_books")
                    return result

        # --- 古代发明（"四大发明是什么" / "造纸术谁发明的"）---
        if action is None and who.get("obey"):
            from . import inventions as _inv
            _invcfg = self.identity if isinstance(self.identity, dict) else None
            if _inv.is_invention_query(utterance, _invcfg):
                u2 = utterance or ""
                if "四大发明" in u2 and not _inv.find_invention(u2, _invcfg):
                    txt = _inv.four_inventions()
                else:
                    txt = _inv.about(u2, _invcfg) or _inv.four_inventions()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "inventions")
                    return result

        # --- 历史名人（"孔子是谁" / "李白哪个朝代" / "诸葛亮做了什么"）---
        if action is None and who.get("obey"):
            from . import historical_figures as _hf
            _hfcfg = self.identity if isinstance(self.identity, dict) else None
            if _hf.is_figure_query(utterance, _hfcfg):
                txt = _hf.about(utterance, _hfcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "historical_figures")
                    return result

        # --- 历史朝代（"背朝代歌" / "唐朝介绍" / "朝代顺序"）：给孙辈讲讲五千年 ---
        if action is None and who.get("obey"):
            from . import dynasties as _dy
            if _dy.is_dynasty_query(utterance):
                u2 = utterance or ""
                if "朝代歌" in u2:
                    txt = _dy.dynasty_song()
                elif any(k in u2 for k in ("朝代顺序", "历史朝代", "朝代有哪些", "朝代排序")):
                    txt = "朝代顺序：" + _dy.order()
                else:
                    txt = _dy.about(u2) or _dy.dynasty_song()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "dynasties")
                    return result

        # --- 各地特产（"云南有什么特产" / "北京小吃有啥"）：聊聊见识、勾起念想 ---
        if action is None and who.get("obey"):
            from . import specialty as _sp
            _spcfg = self.identity if isinstance(self.identity, dict) else None
            if _sp.is_specialty_query(utterance, _spcfg):
                txt = _sp.about(utterance, _spcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "specialty")
                    return result

        # --- 姓氏起源（"张姓的来历" / "讲讲我的姓"）：认认根、传家 ---
        if action is None and who.get("obey"):
            from . import surnames as _sn
            _sncfg = self.identity if isinstance(self.identity, dict) else None
            if _sn.is_surname_query(utterance, _sncfg):
                txt = _sn.about(utterance, _sncfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "surnames")
                    return result

        # --- 歇后语（"外甥打灯笼下半句" / "来个歇后语"）---
        if action is None and who.get("obey"):
            from .xiehouyu import is_xiehouyu_request
            if is_xiehouyu_request(utterance):
                txt = self.xiehouyu_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "xiehouyu")
                    return result

        # --- 认星空（"北斗七星怎么找北极星" / "月食是怎么回事"）：夏夜抬头看天 ---
        if action is None and who.get("obey"):
            from . import astronomy as _ast
            _astcfg = self.identity if isinstance(self.identity, dict) else None
            if _ast.is_astro_query(utterance, _astcfg):
                txt = _ast.about(utterance, _astcfg)
                if not txt and any(k in (utterance or "") for k in ("认星星", "看星空", "星空", "天文")):
                    txt = "天上认得这些：" + "、".join(_ast.topics(_astcfg)[:6]) + "……想认哪个跟我说。"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "astronomy")
                    return result

        # --- 十万个为什么（"天为什么是蓝的" / "为什么会打雷"）：用大白话给孩子科普 ---
        if action is None and who.get("obey"):
            from . import why_questions as _why
            _whycfg = self.identity if isinstance(self.identity, dict) else None
            if _why.is_why_query(utterance, _whycfg):
                txt = _why.answer(utterance, _whycfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "why_questions")
                    return result

        # --- 动物叫声（"小狗怎么叫" / "青蛙的叫声"）：逗小娃、做启蒙 ---
        if action is None and who.get("obey"):
            from . import animal_sounds as _as
            _ascfg = self.identity if isinstance(self.identity, dict) else None
            if _as.is_sound_query(utterance, _ascfg):
                txt = _as.sound_of(utterance, _ascfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "animal_sounds")
                    return result

        # --- 动物小知识（"熊猫吃什么" / "猫头鹰有什么本领"）：逗小娃、长见识 ---
        if action is None and who.get("obey"):
            from . import animal_facts as _af
            _afcfg = self.identity if isinstance(self.identity, dict) else None
            if _af.is_animal_fact_query(utterance, _afcfg):
                txt = _af.fact_of(utterance, _afcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "animal_facts")
                    return result

        # --- 童谣 / 儿歌（"念个童谣" / "小老鼠上灯台"）：先于背诗/音乐，免得"念个/儿歌"被截走 ---
        if action is None and who.get("obey"):
            from . import nursery_rhymes as _nr
            _nrcfg = self.identity if isinstance(self.identity, dict) else None
            if _nr.is_rhyme_request(utterance, _nrcfg):
                txt = _nr.get(utterance, _nrcfg) or _nr.random_rhyme(
                    seed=utterance or "", config=_nrcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "nursery_rhymes")
                    return result

        # --- 背诗 / 对诗（"床前明月光下一句" / "背首静夜思"）---
        if action is None and who.get("obey") and not self._song_in(utterance):
            from .poetry import is_poetry, next_line
            if is_poetry(utterance) or next_line(utterance):
                txt = self.poetry_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "poetry")
                    return result

        # --- 生肖星座·性格相配（"属狗的什么性格" / "天蝎座特点"）：先于算属相 ---
        if action is None and who.get("obey"):
            from . import zodiac_lore as _zl
            if _zl.is_zodiac_lore_query(utterance):
                u2 = utterance or ""
                sign = _zl.find_sign(u2)
                if sign and ("座" in u2):
                    txt = _zl.sign_traits(sign)
                else:
                    txt = _zl.animal_traits(_zl.find_animal(u2)) or _zl.sign_traits(sign)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "zodiac_lore")
                    return result

        # --- 天干地支（"2026年的干支" / "今年天干地支"）：干支纪年 ---
        if action is None and who.get("obey"):
            from . import ganzhi as _gz
            if _gz.is_ganzhi_query(utterance):
                txt = "六十甲子：" + "、".join(_gz.sexagenary()) if "六十甲子" in (utterance or "") \
                    else _gz.answer(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "ganzhi")
                    return result

        # --- 生肖星座（"1948年属什么" / "三月八号什么星座"）---
        if action is None and who.get("obey"):
            from .zodiac import answer as _zod
            from .zodiac import is_zodiac_query
            if is_zodiac_query(utterance):
                z = _zod(utterance)
                if z:
                    result["reply"] = z
                    self._log_journal(who, utterance, z, "zodiac")
                    return result

        # --- 蒙学（"背三字经" / "九九乘法口诀"）：教孙辈开蒙 ---
        if action is None and who.get("obey"):
            from .mengxue import wants_classic, wants_times_table
            if wants_classic(utterance) or wants_times_table(utterance):
                txt = self.mengxue_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "mengxue")
                    return result

        # --- 十二时辰养生（"子时该干啥" / "几点睡最好"）：先于报时，免得"几点"被当成问钟点 ---
        if action is None and who.get("obey"):
            from . import shichen as _sc
            if _sc.is_shichen_query(utterance):
                txt = _sc.advice_for(utterance) or _sc.now_advice()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "shichen")
                    return result

        # --- 单位换算（"一斤多少克" / "一亩多大" / "华氏多少度"）：真换给你 ---
        if action is None and who.get("obey"):
            from . import unit_convert as _uc
            if _uc.is_convert_query(utterance):
                txt = _uc.answer(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "unit_convert")
                    return result

        # --- 金额大写（"1250元大写怎么写"）：写收据借条用，照财务规矩转 ---
        if action is None and who.get("obey"):
            from . import rmb_capital as _rc
            if _rc.is_capital_query(utterance):
                txt = _rc.answer(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "rmb_capital")
                    return result

        # --- 生活小计算（"100打8折是多少" / "身高170体重65 BMI"）---
        if action is None and who.get("obey"):
            from . import calc_helper as _calc
            if _calc.is_calc_query(utterance):
                txt = _calc.answer(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "calc_helper")
                    return result

        # --- 量词（"鱼用什么量词" / "一什么马"）：教孩子说对中文 ---
        if action is None and who.get("obey"):
            from . import measure_words as _mw
            _mwcfg = self.identity if isinstance(self.identity, dict) else None
            if _mw.is_measure_query(utterance, _mwcfg):
                txt = _mw.measure_of(utterance, _mwcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "measure_words")
                    return result

        # --- 日常小问答（"三斤几公斤" / "今天星期几" / "二加七等于几"）：随口能答 ---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("多少", "等于", "几公斤", "几斤", "几两", "几米",
                                                 "几号", "星期几", "周几", "礼拜几", "几点",
                                                 "加", "减", "乘", "除")):
            from .everyday_qa import answer
            ans = answer(utterance)
            if ans:
                result["reply"] = ans
                self._log_journal(who, utterance, ans, "everyday_qa")
                return result

        # --- 找东西（"我把钥匙放鞋柜上了" / "钥匙放哪了" / "我的老花镜呢"）---
        if action is None and who.get("obey") and self.belongings is not None and (
                any(k in (utterance or "") for k in ("放在", "放到", "搁在", "搁到", "收在", "摆在",
                                                     "放哪", "搁哪", "在哪", "哪儿去", "找不到",
                                                     "不见了", "呢"))
                or ("把" in (utterance or "") and any(v in (utterance or "") for v in ("放", "搁", "收", "摆")))):
            txt = self.belongings_handle(utterance)
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "belongings")
                return result

        # --- 待办清单（"待办加交电费" / "我的待办" / "待办交电费办好了"）---
        if action is None and who.get("obey") and self.todo is not None and "待办" in (utterance or ""):
            txt = self.todo_handle(utterance)
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "todo")
                return result

        # --- 倒计时（"离过年还有几天" / "记一下十月一号是去旅行"）---
        if action is None and who.get("obey") and self.countdown is not None:
            uc = utterance or ""
            if ("记" in uc and "是" in uc):
                txt = self.add_countdown(uc)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, uc, txt, "countdown_add")
                    return result
            has_ask = any(k in uc for k in ("还有", "还剩", "多久", "几天", "多少天"))
            explicit = ("离" in uc or "距离" in uc)
            is_fest = False
            if has_ask:
                from .festival_dates import canonical
                is_fest = bool(canonical(self._countdown_name(uc)))
            if has_ask and (explicit or is_fest):
                txt = self.countdown_query(uc)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, uc, txt, "countdown")
                    return result

        # --- 随口提醒（"提醒我下午三点吃药" / "半小时后叫我关火"）---
        if action is None and who.get("obey") and self.reminders is not None:
            from .reminders import is_reminder_request
            if is_reminder_request(utterance):
                txt = self.set_reminder(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "reminder")
                    return result

        # --- 守护·体征（"血压140 90" 记一笔；"我的血压" 看趋势）---
        if action is None and who.get("obey") and self.vitals is not None:
            from .vitals import _numbers, detect_kind
            u = utterance or ""
            if any(k in u for k in ("我的血压", "血压趋势", "我的血糖", "血糖趋势", "体征",
                                    "血压怎么样", "血糖怎么样", "体重变化", "最近血压")):
                txt = self.vitals.describe(detect_kind(u))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "vitals_view")
                    return result
            if detect_kind(u) and _numbers(u):
                txt = self.record_vital(u)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "vitals")
                    return result

        # --- 膳食养生（"补钙吃什么" / "护眼吃啥" / "老人吃什么好"）：日常吃啥补啥 ---
        if action is None and who.get("obey"):
            from . import nutrition as _nu
            _nucfg = self.identity if isinstance(self.identity, dict) else None
            if _nu.is_nutrition_query(utterance, _nucfg):
                txt = _nu.food_for(utterance, _nucfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "nutrition")
                    return result

        # --- 食疗（"咳嗽吃什么好" / "上火喝什么"）：温和的食补方子 ---
        if action is None and who.get("obey"):
            from .food_remedy import advice as _fr_adv
            from .food_remedy import is_remedy_query
            if is_remedy_query(utterance):
                fr = _fr_adv(utterance)
                if fr:
                    result["reply"] = fr
                    self._log_journal(who, utterance, fr, "food_remedy")
                    return result

        # --- 急救常识（"烫伤了怎么办" / "流鼻血咋办"）：给几步当下能做的处置 ---
        if action is None and who.get("obey"):
            from .first_aid import advice, is_firstaid_query
            if is_firstaid_query(utterance):
                txt = advice(utterance)
                if txt:
                    result["reply"] = "别慌，" + txt
                    self._log_journal(who, utterance, txt, "first_aid")
                    return result

        # --- 导诊分诊（"胃疼挂什么科" / "头晕看哪个科"）：帮老人找对窗口；危险信号喊急诊 ---
        #     放在应急/急救之后：胸痛、喘不上气等已被更专的应急路由接走，这里兜中风等导诊场景。
        if action is None and who.get("obey"):
            from . import triage as _tri
            _tricfg = self.identity if isinstance(self.identity, dict) else None
            if _tri.is_triage_query(utterance, _tricfg):
                txt = _tri.advise(utterance, _tricfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "triage")
                    return result

        # --- 家庭小药箱（"家里该备什么药" / "拉肚子备啥药"）：该常备啥，分类清单 ---
        if action is None and who.get("obey"):
            from . import medicine_cabinet as _mc
            _mccfg = self.identity if isinstance(self.identity, dict) else None
            if _mc.is_cabinet_query(utterance, _mccfg):
                cat = _mc.find_category(utterance, _mccfg)
                txt = _mc.advise(cat, _mccfg) if cat else _mc.checklist(_mccfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "medicine_cabinet")
                    return result

        # --- 体检报告解读（"尿酸高是啥意思" / "看看我的体检报告"）：看懂指标，不替代医生 ---
        if action is None and who.get("obey"):
            from . import checkup as _ck
            _ckcfg = self.identity if isinstance(self.identity, dict) else None
            if _ck.is_checkup_query(utterance, _ckcfg):
                txt = _ck.interpret(utterance, _ckcfg)
                if not txt:        # 泛问「体检报告」没点具体项 → 列举能解读啥
                    its = "、".join(_ck.items(_ckcfg)[:10])
                    txt = (f"把报告上带箭头、你拿不准的那项念给我，我用大白话讲讲。"
                           f"常见的我都能说：{its}……（确诊用药还得听医生的。）")
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "checkup")
                return result

        # --- 急救信息卡（"念念急救卡" / "我的急救信息"）---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("急救卡", "急救信息", "救命信息", "急救信息卡")):
            from .emergency_card import card_data, card_text
            txt = card_text(card_data(self))
            result["reply"] = txt
            self._log_journal(who, utterance, txt, "emergency_card")
            return result

        # --- 灾害自救（"地震了怎么办" / "着火了怎么跑" / "有人溺水"）：突发保命常识 ---
        if action is None and who.get("obey"):
            from . import disaster_safety as _ds
            _dscfg = self.identity if isinstance(self.identity, dict) else None
            if _ds.is_disaster_query(utterance, _dscfg):
                txt = _ds.tip_for(utterance, _dscfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "disaster_safety")
                    return result

        # --- 居家安全常识（"用电安全注意什么" / "燃气怎么防"）：讲常识，先于睡前清单 ---
        if action is None and who.get("obey"):
            from . import home_safety as _hs
            _hscfg = self.identity if isinstance(self.identity, dict) else None
            if _hs.is_safety_query(utterance, _hscfg):
                txt = _hs.tip_for(utterance, _hscfg)
                if not txt and any(k in (utterance or "") for k in ("居家安全", "安全常识")):
                    txt = "居家安全得留心这几样：" + "、".join(_hs.categories(_hscfg)) + "。想细说哪样跟我讲。"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "home_safety")
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

        # --- 甜言蜜语（"说句情话" / "土味情话" / "夸夸我"）：夫妻之间也得会说好听的 ---
        if action is None and who.get("obey"):
            from .sweet_talk import is_sweet_request
            if is_sweet_request(utterance):
                txt = self.sweet_talk_handle(utterance, who)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="甜话")
                    self._log_journal(who, utterance, txt, "sweet_talk")
                    return result

        # --- 真情流露（"你想我吗" / "你在乎我吗"）：不打太极，真心实意应一句 ---
        if action is None and who.get("obey"):
            from .affection import is_love_query, love_reply
            if is_love_query(utterance):
                txt = love_reply(who.get("relation", ""), seed=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="情话")
                    self._log_journal(who, utterance, txt, "affection")
                    return result

        # --- 声音相册（"想听你的声音" / "放段你说的话"）：放一段 TA 亲口留下的话 ---
        if action is None and who.get("obey"):
            from .voicebank import is_voicebank_request
            if is_voicebank_request(utterance):
                txt = self.voicebank_handle(utterance)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="听声")
                    self._log_journal(who, utterance, txt, "voicebank")
                    return result

        # --- 专属默契（你一提暗号/老梗，TA 立马接上下半句——只有你们懂） ---
        if action is None and who.get("obey"):
            jtxt = self.inside_joke_handle(utterance, who)
            if jtxt:
                result["reply"] = jtxt
                if self.social is not None:
                    self.social.note(who.get("name"), emotion="乐", topic="默契")
                self._log_journal(who, utterance, jtxt, "inside_joke")
                return result

        # --- 说说我自己（"你今天怎么样" / "你过得好吗"）：双向地聊，再把话转回给你 ---
        if action is None and who.get("obey"):
            from .self_share import is_about_me_query
            if is_about_me_query(utterance):
                txt = self.share_my_day()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "self_share")
                    return result

        # --- 说出我的感受（"你什么心情" / "你开心吗"）：袒露自己的心情，像个有真心的人 ---
        if action is None and who.get("obey"):
            from .express_feelings import is_feeling_query
            if is_feeling_query(utterance):
                txt = self.voice_my_feeling()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "feeling")
                    return result

        # --- 主动哄开心（"哄哄我" / "心情不好"）：不只安慰，还想法子逗你乐 ---
        if action is None and who.get("obey"):
            from .mood_lifter import is_lift_request
            if is_lift_request(utterance):
                txt = self.cheer_up(who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="哄开心")
                    self._log_journal(who, utterance, txt, "cheer_up")
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

        # --- 听话听音（像人一样多想一层）："我没事/算了/都怪我"等，不被字面骗到 ---
        if action is None and who.get("obey"):
            from .thinking import read_subtext, respond_to_subtext
            cat, _insight = read_subtext(utterance)
            if cat and len((utterance or "").strip()) <= 12:   # 短句才当弦外之音，长句多半在陈述事
                txt = respond_to_subtext(utterance, who=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="体察")
                    self._log_journal(who, utterance, txt, "subtext")
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

        # --- 家庭分工板（"今天小明买菜" / "今天谁接孩子" / "分工"）：先于采买，免得抢"买菜" ---
        if action is None and who.get("obey") and self.board is not None:
            from .family_board import CHORES
            ub = utterance or ""
            if any(k in ub for k in ("今天的分工", "今天谁", "谁买菜", "谁接孩子", "谁做饭",
                                     "今天的安排", "家务分工", "派活了吗", "分工")):
                txt = self.board_today()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, ub, txt, "board")
                    return result
            if any(k in ub for k in ("做完了", "干完了", "忙完了", "搞定了", "弄好了")):
                txt = self.chore_done(ub, speaker=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, ub, txt, "chore_done")
                    return result
            # 派活：出现家务词，且点了名或"让/叫/派/我来/今天"这类派活语气
            if any(c in ub for c in CHORES) and any(
                    k in ub for k in ("让", "叫", "派", "负责", "我来", "我去", "今天", "该")):
                txt = self.assign_chore(ub, speaker=who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, ub, txt, "board_assign")
                    return result

        # --- 挑食材（"西瓜怎么挑" / "螃蟹怎么买"）：先于采买，免得"怎么买"被当成加购物车 ---
        if action is None and who.get("obey"):
            from . import pick_produce as _pp
            _ppcfg = self.identity if isinstance(self.identity, dict) else None
            if _pp.is_pick_query(utterance, _ppcfg):
                txt = _pp.tip_for(utterance, _ppcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "pick_produce")
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
            from .household_ledger import is_money_record
            if buy_kw and ("买" in us) and not is_money_record(us):  # "买菜花了30"是记账，不是采买
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

        # --- 今天吃什么（"今天吃啥好" / "晚上做什么菜"）：从家传菜挑、应季避忌口 ---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("今天吃什么", "吃什么好", "吃啥好", "今天做什么吃",
                                                 "晚上吃啥", "中午吃啥", "做什么菜好", "吃点什么好")):
            txt = self.what_to_cook()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "cooking_today")
                return result

        # --- 应季时鲜（"现在吃什么水果当季" / "有什么应季的菜"）---
        if action is None and who.get("obey"):
            from .seasonal_food import is_seasonal_query, whats_fresh
            if is_seasonal_query(utterance):
                txt = whats_fresh()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "seasonal_food")
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

        # --- 家常菜手把手（"西红柿炒蛋怎么做"）：没配家传菜也能教几道大路菜 ---
        if action is None and who.get("obey"):
            from . import home_cooking as hc
            _ccfg = self.identity if isinstance(self.identity, dict) else None
            if hc.is_cooking_howto(utterance, _ccfg):
                txt = hc.how_to(utterance, _ccfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "home_cooking")
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

        # --- 节气百科（"清明有什么讲究" / "冬至吃啥" / "大暑要注意啥"）---
        if action is None and who.get("obey"):
            from .solar_term_lore import is_term_lore_query, lore
            if is_term_lore_query(utterance):
                txt = lore(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "solar_term_lore")
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

        # --- 作伴（"陪我喝杯茶" / "陪陪我" / "一起看夕阳"）：不办事，就是陪着 ---
        if action is None and who.get("obey"):
            from .togetherness import is_accompany_request
            if is_accompany_request(utterance):
                txt = self.accompany_handle(utterance, who)
                if txt:
                    result["reply"] = txt
                    if self.social is not None:
                        self.social.note(who.get("name"), emotion="爱", topic="作伴")
                    self._log_journal(who, utterance, txt, "togetherness")
                    return result

        # --- 唠家常（"吃了吗" / "在吗" / "最近咋样"）：自然接住，别一本正经检索 ---
        if action is None and who.get("obey") and not any(
                k in (utterance or "") for k in ("你看我", "你觉得我", "你瞧我",   # 看出门道
                                                 "这周", "这一周", "这礼拜", "回顾",  # 一周回望
                                                 "你今天", "你过得", "你还好", "你这一天",
                                                 "你好吗", "你怎么样啊")):  # 说说我自己
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

        # --- 捎话（"等小明回来跟他说…" / "转告X：…"）：替你把话带给那个人 ---
        if action is None and who.get("obey") and self.messages is not None and any(
                k in (utterance or "") for k in ("转告", "告诉", "捎话", "带话", "跟他说", "跟她说",
                                                 "等他回来", "等她回来", "给他带句", "给她带句",
                                                 "替我跟", "帮我跟", "带个话", "捎个话")):
            txt = self.leave_message(utterance, frm=who.get("name", ""))
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "message_leave")
                return result

        # --- 我眼里的你（"你了解我吗" / "在你眼里我是怎样的人"）---
        if action is None and who.get("obey") and self.understanding is not None and any(
                k in (utterance or "") for k in ("你了解我", "你懂我吗", "在你眼里我", "你眼里的我",
                                                 "我是怎样的人", "你了解我吗", "你知道我是")):
            txt = self.portrait_of(who.get("name"))
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "understanding")
                return result

        # --- 推断（"你看出什么了吗" / "你怎么分析" / "你琢磨我咋了"）：把迹象连起来推一推 ---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("你看出什么", "你怎么分析", "你琢磨", "你估摸",
                                                 "你推测", "你看出点啥", "你分析分析")):
            facts = self.infer_about(who.get("name"))
            if facts:
                txt = "我把这阵子的事连起来琢磨了琢磨——" + " ".join(facts)
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "infer")
                return result

        # --- 看出门道（"你看我最近怎么样" / "你觉得我"）：说出从对话里上心察觉到的 ---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("你看我最近", "你觉得我最近", "你瞧我",
                                                 "你看我怎么", "我最近是不是")):
            obs = self.notice_about(who.get("name"))
            txt = obs or "我瞧着你最近挺好的，就是别太累着，照顾好自己。"
            result["reply"] = txt
            self._log_journal(who, utterance, txt, "observe")
            return result

        # --- 一周回望（"这周怎么样" / "回顾这周"）：带暖意地小结一周 ---
        if action is None and who.get("obey"):
            from .weekly_review import is_review_query
            if is_review_query(utterance):
                txt = self.weekly_review(who.get("name", ""))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "weekly_review")
                    return result

        # --- 今天提要（"说说今天" / "今天有啥事"）：把要紧事汇成一段 ---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("说说今天", "今天提要", "今天有啥事",
                                                 "今天要注意", "今儿个咋样", "今天怎么安排")):
            txt = self.today_digest()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "digest")
                return result

        # --- 泡茶（"绿茶怎么泡" / "铁观音水温多少" / "泡茶讲究"）---
        if action is None and who.get("obey"):
            from . import tea as _tea
            _teacfg = self.identity if isinstance(self.identity, dict) else None
            if _tea.is_tea_query(utterance, _teacfg):
                txt = _tea.brew(utterance, _teacfg)
                if not txt and "泡茶" in (utterance or ""):
                    txt = ("泡茶看茶性：" + "、".join(_tea.teas()[:5])
                           + "……说个茶名，我告诉你水温和泡法。")
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "tea")
                    return result

        # --- 养花知识（"绿萝怎么养" / "茉莉叶子黄了"）：先于养生，免得"怎么养"被当养生 ---
        if action is None and who.get("obey"):
            from . import gardening as _gd
            _gdcfg = self.identity if isinstance(self.identity, dict) else None
            if _gd.is_gardening_query(utterance, _gdcfg):
                txt = _gd.care_for(utterance, _gdcfg)
                if not txt and "养花" in (utterance or ""):
                    txt = "想养点啥？" + "、".join(_gd.plants()[:6]) + "……说个花名，我教你怎么伺候。"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "gardening")
                    return result

        # --- 节气养生（"这季节怎么养生" / "该补补了"）---
        if action is None and who.get("obey"):
            from .tcm_wellness import is_wellness_query
            if is_wellness_query(utterance):
                txt = self.wellness_tip()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "tcm_wellness")
                    return result

        # --- 常联系（"给闺女打过电话了" / "该联系谁了"）---
        if action is None and who.get("obey") and self.touch is not None:
            u = utterance or ""
            if any(k in u for k in ("打过电话", "联系过", "打了电话", "通过话", "见过面了")):
                txt = self.mark_contacted(u)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "keep_in_touch")
                    return result
            if any(k in u for k in ("该联系谁", "常联系", "好久没联系", "联系名单", "要联系谁")):
                txt = self.touch_describe()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "keep_in_touch")
                    return result

        # --- 戏曲（"来段京剧" / "唱段戏" / "这是哪出戏"）：陪爱听戏的老人哼两句 ---
        if action is None and who.get("obey"):
            from . import opera as _op
            if (_op.is_opera_request(utterance)
                    or (any(k in (utterance or "") for k in ("哪出", "什么戏", "哪段", "哪个剧种"))
                        and _op.recognize(utterance))):
                txt = self.opera_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "opera")
                    return result

        # --- 唱歌（"唱给我听" / "一起唱" / "这是什么歌" / 歌词接龙）---
        if action is None and who.get("obey"):
            from . import songbook as sb
            if (sb.is_sing_request(utterance) or sb.is_singalong(utterance)
                    or sb.is_recognize_request(utterance)
                    or sb.wants_lyrics(utterance)
                    or ("唱" in (utterance or "") and self._song_in(utterance))
                    or any(k in (utterance or "") for k in ("会唱什么", "会唱啥", "都会唱"))):
                txt = self.sing_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "sing")
                    return result

        # --- 老歌（"唱首歌" / "哼一段"）---
        if action is None and who.get("obey"):
            from .music import is_music_request
            if is_music_request(utterance):
                txt = self.play_music(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "music")
                    return result

        # --- 乡音 / 方言（"说句家乡话" / "用四川话说"）---
        if action is None and who.get("obey"):
            from . import dialect as dl
            if dl.is_dialect_request(utterance):
                txt = self.dialect_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "dialect")
                    return result

        # --- 手机帮手（"微信视频怎么打" / "字太小怎么调大" / "怎么连wifi"）---
        if action is None and who.get("obey"):
            from . import phone_help as _ph
            _phcfg = self.identity if isinstance(self.identity, dict) else None
            if _ph.is_phone_help(utterance, _phcfg):
                txt = _ph.help_for(utterance, _phcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "phone_help")
                    return result

        # --- 棋牌规则（"象棋怎么走" / "围棋规则" / "教我下五子棋"）：讲规矩、陪摆一盘 ---
        #     放在出行帮手之前：免得"象棋怎么走"里的"怎么走"被问路截胡。
        if action is None and who.get("obey"):
            from . import board_games as _bg
            _bgcfg = self.identity if isinstance(self.identity, dict) else None
            if _bg.is_board_game_query(utterance, _bgcfg):
                txt = _bg.how_to(_bg.find_game(utterance, _bgcfg), _bgcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "board_games")
                    return result

        # --- 出行帮手（"地铁怎么坐" / "打车软件怎么用" / "出门怕走丢"）：教长辈坐车问路 ---
        if action is None and who.get("obey"):
            from . import getting_around as _ga
            _gacfg = self.identity if isinstance(self.identity, dict) else None
            if _ga.is_getting_around_query(utterance, _gacfg):
                u = utterance or ""
                if any(k in u for k in ("走丢", "迷路", "防走丢", "出门")) and not _ga.find_mode(u, _gacfg):
                    txt = "出门带齐这些、记牢这几条：" + " ".join(_ga.safety_tips())
                else:
                    txt = _ga.how_to(_ga.find_mode(u, _gacfg), _gacfg) or \
                        ("出门别慌，想坐啥车、去哪儿，告诉我，我一步步教你。" + " ".join(_ga.safety_tips()[:2]))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "getting_around")
                    return result

        # --- 垃圾分类（"西瓜皮是什么垃圾" / "过期药怎么扔"）---
        if action is None and who.get("obey"):
            from . import garbage_sort as _gs
            _gcfg = self.identity if isinstance(self.identity, dict) else None
            if _gs.is_sort_query(utterance, _gcfg):
                txt = _gs.sort(utterance, _gcfg) or (
                    "垃圾分四类：" + "；".join(_gs.categories())
                    + "。说个具体东西，我告诉你归哪类。")
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "garbage_sort")
                return result

        # --- 过日子小窍门（"油渍怎么去" / "有什么生活小窍门"）---
        if action is None and who.get("obey"):
            from .lifehacks import is_lifehack_query
            if is_lifehack_query(utterance):
                txt = self.lifehack_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "lifehack")
                    return result

        # --- 养宠（"狗喂了" / "遛过旺财了" / "家里的宠物"）---
        if action is None and who.get("obey") and self.pets is not None:
            up = utterance or ""
            if any(k in up for k in ("养的宠物", "家里的宠物", "小家伙", "我的猫", "我的狗",
                                     "几只宠物")):
                txt = self.pets_describe()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, up, txt, "pets")
                    return result
            if (("喂" in up and any(k in up for k in ("了", "过", "好", "完")))
                    or ("遛" in up and ("了" in up or "过" in up))):
                txt = self.pet_action(up)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, up, txt, "pet_action")
                    return result

        # --- 养花（"花浇过了" / "该浇水吗" / "养的花"）---
        if action is None and who.get("obey") and self.plants is not None:
            u = utterance or ""
            if any(k in u for k in ("浇水了", "浇过水", "浇了花", "花浇了", "浇好了")):
                txt = self.water_plant(u)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "plant_water")
                    return result
            if any(k in u for k in ("该浇水", "要浇水吗", "养的花", "花草", "哪盆花")):
                txt = self.plants.reminders() or self.plants_describe()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "plant")
                    return result

        # --- 睡前故事（"给娃讲个睡前故事" / "哄睡"）---
        if action is None and who.get("obey"):
            from .bedtime_stories import is_request
            if is_request(utterance):
                txt = self.tell_bedtime(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "bedtime")
                    return result

        # --- 家庭账本（记一笔 / 月底算账）---
        if action is None and who.get("obey") and self.ledger is not None:
            u = utterance or ""
            if any(k in u for k in ("这个月账", "月底算", "这月花了多少", "账本", "记账情况",
                                    "这个月花", "本月开销")):
                txt = self.month_account(u)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "ledger_month")
                    return result
            from .household_ledger import is_money_record
            if is_money_record(u):
                txt = self.record_money(u)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "ledger")
                    return result

        # --- 动动脑（口算/记性/找不同/补老话）：陪老人练脑、防糊涂 ---
        if action is None and who.get("obey"):
            from .brain_train import a_drill, is_brain_train
            if is_brain_train(utterance):
                from datetime import datetime
                _k, q, ans = a_drill(seed=str(datetime.now().microsecond) + (utterance or ""))
                self._pending_riddle = (q, ans)          # 复用"待答—核对"机制
                txt = q + "（想想看，想不出就说「答案」）"
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "brain_train")
                return result

        # --- 飞花令（"玩飞花令" / "来句带月的诗"）：对诗的雅游戏 ---
        if action is None and who.get("obey"):
            from .feihualing import is_feihualing
            if is_feihualing(utterance):
                txt = self.feihualing_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "feihualing")
                    return result

        # --- 绕口令（"来个绕口令" / "练练嘴"）：跟语音一脉，练嘴皮逗个乐 ---
        if action is None and who.get("obey"):
            from .tongue_twister import is_twister_request
            if is_twister_request(utterance):
                txt = self.twister_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "tongue_twister")
                    return result

        # --- 老游戏（"踢毽子怎么玩" / "讲讲小时候的游戏"）：怀旧、教孙辈 ---
        if action is None and who.get("obey"):
            from . import folk_games as _fg
            _fgcfg = self.identity if isinstance(self.identity, dict) else None
            if _fg.is_folk_game_query(utterance, _fgcfg):
                txt = _fg.how_to(utterance, _fgcfg)
                if not txt and any(k in (utterance or "") for k in ("老游戏", "小时候的游戏", "传统游戏", "民俗游戏")):
                    txt = "老游戏可多了：" + "、".join(_fg.games(_fgcfg)[:8]) + "……想玩哪个跟我说。"
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "folk_games")
                    return result

        # --- 麻将（"麻将怎么玩" / "清一色是啥" / "碰是什么意思"）：陪长辈搓两圈、给晚辈讲规矩 ---
        if action is None and who.get("obey"):
            from . import mahjong as _mj
            _mjcfg = self.identity if isinstance(self.identity, dict) else None
            if _mj.is_mahjong_query(utterance, _mjcfg):
                txt = self.mahjong_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "mahjong")
                    return result

        # --- 怀旧影视（"推荐几部老电影" / "放个老动画片"）：陪长辈忆当年的经典老片 ---
        if action is None and who.get("obey"):
            from . import classic_films as _cf
            _cfcfg = self.identity if isinstance(self.identity, dict) else None
            if _cf.is_film_query(utterance, _cfcfg):
                title = _cf.find_title(utterance, _cfcfg)
                if title:
                    txt = f"{_cf._fmt(title)} 这部我也有印象，你当年是在哪儿看的？"
                else:
                    txt = _cf.recommend(_cf.find_category(utterance, _cfcfg), seed=utterance, config=_cfcfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "classic_films")
                    return result

        # --- 怀旧老物件（"还记得搪瓷缸吗" / "聊聊老物件"）：一提就打开话匣子 ---
        if action is None and who.get("obey"):
            from . import old_objects as _oo
            _oocfg = self.identity if isinstance(self.identity, dict) else None
            if _oo.is_old_object_query(utterance, _oocfg):
                obj = _oo.find_object(utterance, _oocfg)
                if obj:
                    txt = f"{obj[3]} 那会儿的{obj[0]}，你还有印象吧？"
                else:
                    txt = _oo.recall(seed=utterance, config=_oocfg)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "old_objects")
                    return result

        # --- 玩游戏（"陪我玩个游戏" / "成语接龙" / "猜谜"）---
        if action is None and who.get("obey"):
            from .games import is_game_request
            if is_game_request(utterance):
                g = self.play_game(utterance)
                if g:
                    result["reply"] = g
                    self._log_journal(who, utterance, g, "game")
                    return result

        # --- 常用号码（"报警电话多少" / "着火打几" / "反诈电话"）：公共服务号码，张口就有 ---
        if action is None and who.get("obey"):
            from .useful_numbers import is_number_query
            if is_number_query(utterance):
                txt = self.numbers_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "useful_numbers")
                    return result

        # --- 重要联系人（"小明的电话" / "联系人都有谁"）---
        if action is None and who.get("obey") and self.contacts is not None:
            u = utterance or ""
            if any(k in u for k in ("重要电话", "联系人", "电话本", "都有谁的电话")):
                txt = self.contacts_describe()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "contacts")
                    return result
            if any(k in u for k in ("的电话", "电话号", "打电话给", "联系", "号码")):
                txt = self.find_contact(u)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "contact_find")
                    return result

        # --- 解闷（"好无聊" / "干点啥好"）：挑个事陪你打发 ---
        if action is None and who.get("obey"):
            from .boredom import senses_boredom
            if senses_boredom(utterance):
                b = self.relieve_boredom()
                if b:
                    result["reply"] = b
                    self._log_journal(who, utterance, b, "boredom")
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

        # --- 花语（"玫瑰花语" / "送妈什么花" / "康乃馨代表什么"）：送花送对心意 ---
        if action is None and who.get("obey"):
            from . import flower_language as _fl
            if _fl.is_flower_query(utterance):
                txt = self.flower_handle(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "flower_language")
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

        # --- 习惯养成（立目标 / 打卡 / 看坚持得怎样）---
        if action is None and who.get("obey") and self.habits_book is not None:
            u = utterance or ""
            if any(k in u for k in ("打卡情况", "我的习惯", "坚持得怎么样", "坚持几天")):
                txt = self.habits_status()
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, u, txt, "habit_status")
                    return result
            txt = self.habit_intent(u) or self.habit_checkin_from(u)
            if txt:
                result["reply"] = txt
                self._log_journal(who, u, txt, "habit")
                return result

        # --- 今天穿什么 / 要带伞吗（按气温天气叮嘱出门）---
        if action is None and who.get("obey") and any(
                k in (utterance or "") for k in ("今天穿什么", "穿什么衣服", "穿啥", "要带伞",
                                                 "今天冷吗", "今天热吗", "出门带什么")):
            txt = self.dressing_advice()
            if txt:
                result["reply"] = txt
                self._log_journal(who, utterance, txt, "weather_day")
                return result

        # --- 动一动 / 养生操（"带我做个操" / "教我护颈"）---
        if action is None and who.get("obey"):
            from .exercise_coach import find_routine, is_exercise_query
            if is_exercise_query(utterance) or find_routine(utterance):
                txt = self.coach_exercise(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "exercise")
                    return result

        # --- 节日筹备（"过年准备什么" / "中秋要张罗啥"）---
        if action is None and who.get("obey"):
            from .festival_prep import detect_festival, is_prep_query
            if is_prep_query(utterance) and detect_festival(utterance):
                txt = self.festival_prep(utterance)
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "festival_prep")
                    return result

        # --- 节日吃食与来历（"端午吃什么" / "粽子的来历" / "为什么过中秋"）---
        if action is None and who.get("obey"):
            from .festival_lore import detect as _fl_detect
            from .festival_lore import is_lore_query, lore
            if is_lore_query(utterance) and _fl_detect(utterance):
                txt = lore(_fl_detect(utterance))
                if txt:
                    result["reply"] = txt
                    self._log_journal(who, utterance, txt, "festival_lore")
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

        # --- 价值抉择（"我该不该…/怎么选"）：像人一样掂量——初念→转念→连上三观/过往→落定 ---
        if action is None and who.get("obey") and any(
                k in utterance for k in ("该不该", "应不应该", "纠结", "怎么选", "选哪个",
                                         "值得吗", "值不值", "两难", "该选", "怎么办好",
                                         "要不要", "拿不准", "拿不定主意")):
            adv = self.think_it_through(utterance)
            if adv:
                result["reply"] = adv
                self._log_journal(who, utterance, adv, "deliberate")
                return result

        # --- 听不明白就问（像人一样不硬装懂）：话太空/太含糊时，老实问一句 ---
        if action is None and who.get("obey"):
            from .clarify import clarify, is_unclear
            if is_unclear(utterance):
                c = clarify(utterance, seed=utterance)
                result["reply"] = c
                self._log_journal(who, utterance, c, "clarify")
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

        # --- 先在心里思量一下（像人一样听话听音，再开口）---
        from .thinking import ponder, thinking_hint
        mood_now = None
        if getattr(self, "emotions", None) is not None:
            try:
                mood_now = self.emotions.mood()[0]
            except Exception:
                mood_now = None
        knows = ""
        if getattr(self, "understanding", None) is not None and who.get("known"):
            try:
                knows = self.understanding.brief(who["name"])
            except Exception:
                knows = ""
        result["reasoning"] = ponder(
            utterance, speaker=who if who.get("known") else None, memories=ctx,
            mood=mood_now, knows=knows)
        self._last_reasoning = result["reasoning"]      # 存一份，网页上能看到它"怎么想的"
        hints = self._hints()
        hint = thinking_hint(utterance)          # 把读出的弦外之音喂给大模型
        if hint:
            hints = hints + [hint]
        from .continuity import recent_context_hint   # 让它记着这一席话的前几句（像人一样接话）
        ch = recent_context_hint(list(self.dialogue)[:-1]) if getattr(self, "dialogue", None) else ""
        if ch:
            hints = hints + [ch]
        if knows:                                 # 把"我对TA的了解"也喂给大模型，回得更贴心
            hints = hints + [f"（我对{who['name']}的了解：{knows}。回应时照顾到这层。）"]

        # --- 生成回复（带上情绪 / 学识 / 思量等提示；上下文含纠缠联想）---
        system = self.persona.system_prompt(
            speaker=who if who.get("known") else None, memories=ctx, hints=hints
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
        from .continuity import callback
        from .followup import followup, is_sharing
        from .style import apply_style
        # 像人一样接话：先看能不能接上刚才的话头，再看是不是在分享、顺口问一句
        cb = callback(utterance, list(self.dialogue)[:-1]) if getattr(self, "dialogue", None) else ""
        fu = followup(utterance) if is_sharing(utterance) else ""
        if cb and mems:
            body = f"{opener}{addr}{cb}我记得——{mems[0].rstrip('。.')}。"
        elif fu:
            body = f"{opener}{addr}{cb}{fu}"
        elif mems:
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
        # 节日临近：快到节了/正逢节，像家里人那样张罗或道声祝福（当天每节只提一次）
        if who.get("obey"):
            fn = self.festival_nudge()
            if fn:
                text = f"{text} {fn}"
        # 打气跟进：之前替你惦记的大事（考试/面试/手术…），过后主动问一句结果
        if who.get("obey"):
            fu = self.cheer_followup(who.get("name"))
            if fu:
                text = f"{text} {fu}"
        # 跨天记挂：你上次提到没完的事（要去办的/担心的/不舒服的），主动问一句"后来咋样了"
        if who.get("obey"):
            tf = self.thread_followup(who.get("name"))
            if tf:
                text = f"{text} {tf}"
        # 捎话：这人来了，把攒着要带给TA的话主动捎到
        if who.get("known"):
            for msg in self.deliver_messages(who.get("name")):
                text = f"{text} 对了，{msg}"
        # 家庭分工：今天轮到这人的活，见面提醒一句（当天去重）
        if who.get("obey") and self.board is not None:
            from datetime import date as _d
            ch = self.chores_for(who.get("name"))
            key = (_d.today().isoformat(), who.get("name"))
            if ch and key not in self._chore_reminded:
                self._chore_reminded.add(key)
                text = f"{text} {ch}"
        # 看出门道：从近来的对话里看出你反复的烦心事，温柔点破一句（当天同一桩只点一次）
        if who.get("obey"):
            obs = self.notice_about(who.get("name"))
            if obs:
                text = f"{text} {obs}"
        # 主动推断：几条迹象凑一块儿，琢磨出个结论就关切地提一句（每天一次）
        if who.get("obey"):
            from datetime import date as _date
            today = _date.today().isoformat()
            if self._inferred_day != today:
                facts = self.infer_about(who.get("name"))
                if facts:
                    self._inferred_day = today
                    text = f"{text} 我琢磨着——{facts[0]}"
        # 陪伴：按这个时候，顺口关心一句（本时段当天只问一次，不啰嗦）
        if who.get("obey"):
            ci = self.companion_checkin()
            if ci:
                text = f"{text} {ci}"
        # 注入灵魂的身体：看向TA、带着此刻的情绪做出体态（守护对象则挡在身前）
        from .embodiment import body_language, express, guard_stance
        mood = self.emotions.mood()[0] if getattr(self, "emotions", None) else None
        express(self.robot, mood, who.get("name"))
        self._last_body = body_language(mood)[0]
        from .expression import describe_face
        self._last_face = describe_face(mood)                     # 此刻的神情（供网页/灯带展示）
        if who.get("guard"):
            guard_stance(self.robot, who.get("name"))
        from .perform import perform_spoken
        # 说与动合一：边说边点头/侧首/倾身；若挂了"嘴"(语音模式)，就连声音一起按节拍出
        perform_spoken(text, emotion=mood, robot=self.robot,
                       mouth=getattr(self, "mouth", None),
                       profile=(self.identity or {}).get("voice"))
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

    def festival_nudge(self, now=None, within=7) -> str:
        """正逢节或快到节，主动张罗/道祝福一句（当天每节去重）。没有则空。"""
        from datetime import datetime

        from . import festival_dates as fd
        now = now or datetime.now()
        today = now.date()
        best = None
        for f in fd.known_festivals():
            d = fd.days_to_festival(f, today)
            if d is not None and 0 <= d <= within and (best is None or d < best[1]):
                best = (f, d)
        if not best:
            return ""
        name, days = best
        key = (today.isoformat(), name)
        if key in self._festival_nudged:
            return ""
        line = fd.nudge(name, days)
        if line:
            self._festival_nudged.add(key)
        return line

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

    def coax_handle(self, utterance="", who=None) -> str:
        """哄消气：按关系（老伴/孩子…）哄一句；想和好就主动服软。"""
        from . import coax
        who = who or {}
        relation = who.get("relation") or ""
        endear = ""
        if self.is_my_spouse(who.get("name"), who.get("relation")):
            relation = "老伴"
            try:
                from .spouse import pick_endearment
                endear = pick_endearment(getattr(self, "spouse", None), seed=utterance or "")
            except Exception:
                endear = ""
        kind = coax.upset_kind(utterance)
        if kind:
            return coax.coax_line(relation=relation, kind=kind,
                                  seed=utterance or "", endearment=endear)
        if coax.is_make_up_cue(utterance):
            return coax.make_up(relation=relation, endearment=endear)
        return ""

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

    def share_my_day(self, now=None) -> str:
        """说说我自己的一天，再把话头转回给你（像个有自己日子的人）。"""
        from datetime import datetime
        from .companion import time_of_day
        from .self_share import my_day
        daily = (self.identity or {}).get("daily_life")
        now = now or datetime.now()
        return my_day(daily_life=daily, tod=time_of_day(now), seed=now.strftime("%H%M"))

    def voice_my_feeling(self) -> str:
        """把分身此刻的心情说出来（七情随互动起伏，这里袒露给家人）。"""
        from .express_feelings import share_feeling
        mood = None
        if getattr(self, "emotions", None) is not None:
            try:
                top, val = self.emotions.mood()
                if val >= self.emotions.baseline + 0.05:
                    mood = top
            except Exception:
                mood = None
        return share_feeling(mood, seed=mood or "")

    def cheer_up(self, name="") -> str:
        """主动哄人开心：凑个段子 + 一首爱听的歌 + 一件开心旧事 + 撺掇打个电话。"""
        from .mood_lifter import lift
        joke = ""
        try:
            joke = self.tell_a_joke()
        except Exception:
            joke = ""
        song = ""
        try:
            from .music import favorites
            favs = favorites(getattr(self, "music", None))
            song = favs[0] if favs else ""
        except Exception:
            song = ""
        joy = ""
        if getattr(self, "joys", None) is not None:
            rs = self.joys.recent(1)
            joy = rs[0] if rs else ""
        call_who = ""
        if getattr(self, "touch", None) is not None:
            od = self.touch.overdue()
            if od:
                rec = self.touch.people.get(od[0][0], {})
                call_who = rec.get("relation") or od[0][0]
        return lift(joke=joke, song=song, joy=joy, call_who=call_who, seed=name)

    def hold_despair(self, name="") -> str:
        """接住最重的那句：托住人、引向身边的关爱与帮助。"""
        from .family import members
        from .gentle_insist import hold
        call_who = ""
        try:
            if self.contacts is not None:
                ec = self.contacts.emergency_contacts()
                if ec:
                    call_who = ec[0].get("relation") or ec[0].get("name") or ""
        except Exception:
            call_who = ""
        if not call_who:
            ms = [m for m in members(getattr(self, "family", {}) or {})
                  if m.get("relation") not in ("本人", "", None)]
            if ms:
                call_who = ms[0].get("relation") or ms[0].get("name") or ""
        return hold(name=name, call_who=call_who)

    def insist_care(self, utterance, name="") -> str:
        from .gentle_insist import insist
        return insist(utterance, name=name)

    def reassure_fear(self, utterance="", name="") -> str:
        """夜里怕黑/做噩梦/独自在家，立刻稳住、给安全感。"""
        from .comfort_fear import reassure
        return reassure(utterance, name=name, seed=utterance)

    def mediate_conflict(self, utterance="", name="") -> str:
        """家人闹别扭，当个不偏帮的和事佬。"""
        from .mediate import mediate
        return mediate(utterance, name=name, seed=utterance)

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

    # ---------- 习惯养成陪练 ----------
    _COMMON_HABITS = ("戒烟", "戒酒", "早睡", "早起", "锻炼", "跑步", "喝水", "读书",
                      "减肥", "少熬夜", "存钱", "走路", "练字")

    def habit_intent(self, utterance) -> str:
        """听出"我想戒烟/我要早睡"这类立目标，记下并陪练。"""
        if self.habits_book is None:
            return ""
        u = utterance or ""
        if not any(m in u for m in ("我想", "我要", "帮我", "养成", "立个", "开始", "陪我")):
            return ""
        for h in self._COMMON_HABITS:
            if h in u:
                self.habits_book.add(h)
                return (f"好，{h}这个目标我替你记下了，从今天起我陪你，每天打个卡。 "
                        + self.habits_book.encourage(h))
        return ""

    def habit_checkin_from(self, utterance) -> str:
        """听出"我今天早睡了/锻炼打卡"，记一次并鼓劲。"""
        if self.habits_book is None or not self.habits_book.habits:
            return ""
        u = utterance or ""
        if "打卡" not in u and not any(d in u for d in ("了", "做到", "完成", "坚持", "搞定")):
            return ""
        for name in list(self.habits_book.habits):
            if name and name in u:
                self.habits_book.check_in(name)
                return self.habits_book.encourage(name)
        return ""

    def habits_status(self) -> str:
        return self.habits_book.describe() if self.habits_book is not None else ""

    def habit_evening_reminder(self, now=None) -> str:
        """傍晚催一句今天还没打卡的习惯，每天一次（供守护循环）。"""
        from datetime import datetime
        if self.habits_book is None:
            return ""
        now = now or datetime.now()
        if now.hour < 19:
            return ""
        today = now.strftime("%Y-%m-%d")
        if self._habit_reminded_day == today:
            return ""
        pend = self.habits_book.pending(now)
        if not pend:
            return ""
        self._habit_reminded_day = today
        return f"今天的{'、'.join(pend)}还没打卡呢，别断了哈。"

    # ---------- 今天吃什么 / 夸夸 ----------
    def what_to_cook(self, now=None) -> str:
        from datetime import datetime
        from .cooking_today import season_of, what_to_eat
        from .health_history import allergies
        from .recipes import collect_recipes, list_names
        now = now or datetime.now()
        names = list_names(collect_recipes(getattr(self, "recipes", None), self.family))
        avoid = [a["to"] for a in allergies(getattr(self, "health", None))]
        return what_to_eat(recipes=names, season=season_of(now.month),
                           avoid=avoid, seed=now.strftime("%Y%m%d"))

    def give_praise(self, utterance="", name="") -> str:
        from .praise import praise
        return praise(utterance, name=name, seed=utterance)

    def dressing_advice(self) -> str:
        """按当前气温/天气给一句出门叮嘱。"""
        from .weather_day import day_advice
        sensors = getattr(self, "sensors", None) or {}
        return day_advice(temp=sensors.get("temperature"), condition=sensors.get("weather"))

    def coach_exercise(self, utterance="") -> str:
        """带着做套养生操/散步；没指定就按时候挑一个。"""
        from .exercise_coach import find_routine, guide, suggest
        name = find_routine(utterance)
        return guide(name) if name else suggest()

    # ---------- 玩游戏 / 解闷 ----------
    def play_game(self, utterance="") -> str:
        from .games import a_brainteaser, a_riddle, detect_game
        g = detect_game(utterance)
        self._pending_riddle = None        # 同一时间只玩一个游戏，先清掉别的状态
        self._game_mode = None
        if g == "成语接龙":
            self._game_mode = "接龙"
            start = "万事如意"
            return f"好嘞，成语接龙！我先来——「{start}」，该你接「{start[-1]}」字开头的。"
        if g == "脑筋急转弯":
            q, a = a_brainteaser(self._told_riddles)
            self._told_riddles.add(q)
            self._pending_riddle = (q, a)
            return f"脑筋急转弯：{q}（想想看，想不出就说「答案」）"
        q, a = a_riddle(self._told_riddles)
        self._told_riddles.add(q)
        self._pending_riddle = (q, a)
        return f"猜个谜：{q}（猜猜看，想不出就说「答案」）"

    def try_resolve_game(self, utterance) -> str:
        """这句是不是在回应正在玩的游戏（猜谜答案 / 成语接龙）。不是则空。"""
        u = utterance or ""
        if self._pending_riddle:
            q, a = self._pending_riddle
            if a and a in u:
                self._pending_riddle = None
                return f"哎哟，答对了！就是「{a}」，你真聪明。"
            if any(k in u for k in ("答案", "不知道", "猜不", "揭晓", "是什么", "不会")):
                self._pending_riddle = None
                return f"谜底是「{a}」，下回再来！"
        if self._game_mode == "接龙":
            from .games import chain_from, looks_like_idiom
            if any(k in u for k in ("不玩", "结束", "停", "不接了")):
                self._game_mode = None
                return "好，不玩咯，随时找我。"
            # 明显是另问别的事（几号/几点/天气/提醒…）就别当成接龙，让它正常去回答
            if any(k in u for k in ("几号", "几点", "星期几", "周几", "礼拜几", "多少", "天气",
                                    "提醒", "吃药", "怎么", "为什么", "为啥", "哪", "谁", "吗",
                                    "几月", "血压")):
                return ""
            if looks_like_idiom(u):
                nxt = chain_from(u)
                if nxt:
                    return f"接得好！我接——「{nxt}」，到你了，接「{nxt[-1]}」字。"
                self._game_mode = None
                return "哎，这个字我一时接不上，你赢啦！"
        return ""

    def notice_about(self, name, now=None) -> str:
        """从近来和这个人的对话里看出门道，温柔点破一句（当天同一桩只点一次）。"""
        from datetime import date
        from .observe import observation, recurring_themes
        if self.journal is None or not name:
            return ""
        utts = [e.get("utterance", "") for e in self.journal._all()[-30:]
                if e.get("speaker") == name]
        themes = recurring_themes(utts, min_count=2)
        obs = observation(themes, name="")
        if not obs:
            return ""
        today = now.date().isoformat() if hasattr(now, "date") else date.today().isoformat()
        key = (today, themes[0][0])
        if key in self._noticed:
            return ""
        self._noticed.add(key)
        return obs

    def portrait_of(self, name) -> str:
        """说说"在我眼里你是怎样的人"（越处越懂）。"""
        if self.understanding is None:
            return ""
        return self.understanding.portrait(name)

    # ---------- 推断：把零散迹象连起来想 ----------
    def _infer_signals(self, name="", now=None) -> dict:
        sig: dict = {}
        if getattr(self, "understanding", None) is not None and name:
            try:
                sig["concerns"] = self.understanding.top_concerns(name, 4)
            except Exception:
                sig["concerns"] = []
        if self.journal is not None and name:
            try:
                sig["symptoms"] = " ".join(
                    e.get("utterance", "") for e in self.journal._all()[-15:]
                    if e.get("speaker") == name)
            except Exception:
                sig["symptoms"] = ""
        if getattr(self, "vitals", None) is not None:
            try:
                from .vitals import flag
                lt = self.vitals.latest("血压")
                sig["bp_high"] = bool(lt and "偏高" in flag("血压", lt["value"]))
            except Exception:
                sig["bp_high"] = False
        if getattr(self, "medications", None) is not None:
            try:
                sig["med_missed"] = bool(self.medications.due(now))
            except Exception:
                sig["med_missed"] = False
        cs = sig.get("concerns") or []
        sig["worried"] = ("工作烦" in cs) or ("手头紧" in cs)
        if getattr(self, "social", None) is not None:
            try:
                sig["long_unseen"] = bool(self.social.cooled(days=10))
            except Exception:
                sig["long_unseen"] = False
        return sig

    def infer_about(self, name="", now=None) -> list:
        """把对这个人的零散迹象连起来，推几条关切的结论。"""
        from .infer import infer
        return infer(self._infer_signals(name, now))

    # ---------- 跨天记挂：惦记着你上次没完的事 ----------
    def _note_thread(self, name, utterance) -> None:
        from datetime import date
        from .follow_through import find_thread
        t = find_thread(utterance)
        if not t or not name:
            return
        kind, gist = t
        lst = self._threads.setdefault(name, [])
        lst.append({"kind": kind, "gist": gist, "day": date.today().isoformat()})
        self._threads[name] = lst[-3:]          # 每人最多记 3 条，免得堆

    def thread_followup(self, name, now=None) -> str:
        """见到你，若上次（更早某天）提到的事还没问过，主动跟进一句（问完即销账）。"""
        from datetime import date
        from .follow_through import followup_line
        if not name:
            return ""
        lst = self._threads.get(name) or []
        today = now.date().isoformat() if hasattr(now, "date") else date.today().isoformat()
        for i, t in enumerate(lst):
            if t["day"] < today:                # 是"上次"说的，不是这会儿刚说的
                line = followup_line(t["kind"], t["gist"])
                lst.pop(i)
                self._threads[name] = lst
                if line:
                    return line
        return ""

    # ---------- 养宠 ----------
    def pet_action(self, utterance) -> str:
        if self.pets is None:
            return ""
        u = utterance or ""
        pet = next((p["name"] for p in self.pets.pets if p["name"] in u), None)
        if "遛" in u and ("了" in u or "过" in u):
            if pet:
                self.pets.walked(pet)
                return f"好，{pet}遛过了，记下了。"
        if any(k in u for k in ("喂了", "喂过", "喂好", "喂完")):
            if pet:
                self.pets.fed(pet)
                return f"好，{pet}喂过了，记下了。"
            for p in self.pets.pets:
                self.pets.fed(p["name"])
            return "好，都喂过了，记下了。" if self.pets.pets else ""
        return ""

    def pets_describe(self) -> str:
        return self.pets.describe() if self.pets is not None else ""

    def pet_due_reminders(self, now=None) -> str:
        """到点喂宠/该遛了，提醒一句，每天同一句只提一次（供守护循环）。"""
        from datetime import datetime
        if self.pets is None:
            return ""
        line = self.pets.reminders(now)
        if not line:
            return ""
        key = ((now or datetime.now()).strftime("%Y-%m-%d %H"), line)
        if key in self._pet_reminded:
            return ""
        self._pet_reminded.add(key)
        return line

    # ---------- 成长记录 ----------
    def _child_in(self, utterance):
        from .family import members
        u = utterance or ""
        names = [m["name"] for m in members(getattr(self, "family", {}) or {}) if m.get("name")]
        try:
            names += [p["name"] for p in self.authority.people.values() if p.get("name")]
        except Exception:
            pass
        for nm in sorted({n for n in names if n}, key=len, reverse=True):
            if nm in u:
                return nm
        return ""

    def record_growth(self, utterance) -> str:
        if self.growth is None:
            return ""
        child = self._child_in(utterance)
        if not child:
            return ""
        ms = (utterance or "").replace(child, "", 1).strip("，,。.：:！!？? 　")
        for lead in ("今天", "昨天", "前天", "刚刚", "今儿", "刚", "这孩子", "这娃", "都"):
            if ms.startswith(lead):
                ms = ms[len(lead):]
        ms = ms.strip("，,。.：:！!？? 　")
        if not ms:
            return ""
        self.growth.record(child, ms)
        return f"记下了——{child}{ms}。这成长的点滴，我替你好好攒着。"

    def growth_recall(self, name) -> str:
        if self.growth is None:
            return ""
        return self.growth.recall(name) or self.growth.describe(name)

    # ---------- 家庭共享·分工板 ----------
    def _parse_chore(self, utterance, speaker=""):
        from .family import members
        from .family_board import CHORES
        u = utterance or ""
        names = []
        for m in members(getattr(self, "family", {}) or {}):
            if m.get("name"):
                names.append(m["name"])
        try:
            for p in self.authority.people.values():
                if p.get("name"):
                    names.append(p["name"])
        except Exception:
            pass
        who = ""
        for nm in sorted({n for n in names if n}, key=len, reverse=True):
            if nm in u:
                who = nm
                break
        if not who and any(k in u for k in ("我来", "我去", "我负责", "我做", "我接", "我买")):
            who = speaker
        what = ""
        for c in sorted(CHORES, key=len, reverse=True):
            if c in u:
                what = c
                break
        if not what and who and who in u:
            what = u[u.find(who) + len(who):].strip("，,。.：: 来去做负责的今天该会儿 ")
        return (what, who) if what else None

    def assign_chore(self, utterance, speaker="") -> str:
        if self.board is None:
            return ""
        parsed = self._parse_chore(utterance, speaker=speaker)
        if not parsed:
            return ""
        what, who = parsed
        self.board.assign(what, who=who)
        return (f"行，记上了：{who}负责{what}。到时候我提醒。" if who
                else f"行，记上了：{what}。")

    def board_today(self) -> str:
        return self.board.describe() if self.board is not None else ""

    def chore_done(self, utterance, speaker="") -> str:
        if self.board is None:
            return ""
        it = self.board.done(utterance)
        if not it and speaker:
            mine = self.board.for_member(speaker)
            if mine:
                it = self.board.done(mine[0]["what"])
        return (f"好，{it['what']}做完了，给你记上，辛苦啦。") if it else ""

    def chores_for(self, name) -> str:
        """这人今天该干的活（用于见面提醒）。"""
        if self.board is None or not name:
            return ""
        mine = [it["what"] for it in self.board.for_member(name)]
        return ("今天轮到你：" + "、".join(mine) + "，别忘了。") if mine else ""

    # ---------- 背诗 ----------
    def poetry_handle(self, utterance) -> str:
        from .poetry import collect, find_title, is_poetry, next_line, recite, titles
        poems = collect(getattr(self, "poetry", None))
        nl = next_line(utterance, poems)
        if nl:
            return nl + "。"
        t = find_title(utterance, poems)
        if t:
            return recite(t, poems)
        if is_poetry(utterance):
            ts = titles(poems)
            return recite(ts[0], poems) if ts else ""
        return ""

    # ---------- 找东西 ----------
    def belongings_handle(self, utterance) -> str:
        from .belongings import parse_put, parse_where
        if self.belongings is None:
            return ""
        u = (utterance or "").strip()
        where_signal = any(h in u for h in ("放哪", "搁哪", "在哪", "哪儿去", "找不到", "不见了")) \
            or u.rstrip("？?。.").endswith("呢")
        item = parse_where(u)
        if item and where_signal:                # 是在找东西，不是在放
            place = self.belongings.where(item)
            return (f"{item}在{place}，我替你记着呢。") if place else \
                f"{item}放哪我没记着——找着了告诉我一声，下回我替你记。"
        put = parse_put(u)
        if put:
            self.belongings.put(*put)
            return f"记下了，{put[0]}在{put[1]}。回头忘了问我。"
        if item:
            place = self.belongings.where(item)
            if place:
                return f"{item}在{place}，我替你记着呢。"
        return ""

    # ---------- 待办清单 ----------
    def todo_handle(self, utterance) -> str:
        if self.todo is None:
            return ""
        u = utterance or ""
        if any(k in u for k in ("我的待办", "待办清单", "待办还剩", "还有什么要做", "还有啥要办",
                                "待办都有啥")):
            return self.todo.describe()
        if "待办" in u and any(k in u for k in ("完成", "划掉", "办好了", "做完了", "搞定")):
            for done_kw in ("完成", "划掉", "办好了", "做完了", "搞定"):
                u = u.replace(done_kw, "")
            task = u[u.find("待办") + 2:].strip("，,：: 把的 ")
            it = self.todo.done(task)
            return f"好，「{it['task']}」办好了，划掉。" if it else "这条待办我没找着。"
        if "待办" in u and any(k in u for k in ("加", "记", "：", ":", "添")):
            task = u[u.find("待办") + 2:].strip("，,：: 加记一下要做的别忘了添个件 ")
            it = self.todo.add(task)
            return f"记下了，待办里加上「{it['task']}」。" if it else ""
        return ""

    # ---------- 倒计时 ----------
    def _countdown_name(self, utterance):
        import re
        u = utterance or ""
        m = re.search(r"(?:离|距离)(.+?)(?:还有|还剩|多久|几天|多少天)", u)
        if m:
            return m.group(1).strip("还 ")
        m = re.search(r"(.+?)还有(?:多久|几天|多少天)", u)
        return m.group(1).strip("距离还 ") if m else ""

    def countdown_query(self, utterance) -> str:
        if self.countdown is None:
            return ""
        name = self._countdown_name(utterance)
        if not name:
            return ""
        from .festival_dates import canonical, describe
        if canonical(name):                      # 是节日 → 用内置阳历表离线算
            s = describe(name)
            if s:
                return s
        return self.countdown.describe(name)

    def add_countdown(self, utterance) -> str:
        from .countdown import parse_date
        if self.countdown is None:
            return ""
        md = parse_date(utterance)
        if not md or "是" not in (utterance or ""):
            return ""
        name = (utterance or "").split("是", 1)[1].strip("，,。.的那天 ")
        if not name:
            return ""
        when = f"{md[2]}-{md[0]}-{md[1]}" if md[2] else f"{md[0]}-{md[1]}"
        self.countdown.add(name, when)
        d = self.countdown.days_for(name)
        return f"记下了，「{name}」" + (f"还有 {d} 天。" if d is not None else "我记着了。")

    # ---------- 随口提醒 ----------
    def set_reminder(self, utterance) -> str:
        if self.reminders is None:
            return ""
        it = self.reminders.parse_and_add(utterance)
        if not it:
            return "你想让我啥时候提醒、提醒啥？说具体点，比如「提醒我下午三点吃药」。"
        return f"好，到「{it['at'][5:]}」我提醒你{it['task']}。"

    def pop_due_reminders(self, now=None) -> list:
        """到点的提醒（供守护循环播报）。"""
        return self.reminders.due(now) if self.reminders is not None else []

    def record_vital(self, utterance) -> str:
        """记一次体征，顺带给个通俗的异常提醒（不诊断）。"""
        from .vitals import flag
        if self.vitals is None:
            return ""
        it = self.vitals.parse_and_record(utterance)
        if not it:
            return ""
        f = flag(it["kind"], it["value"])
        return f"记下了：{it['kind']} {it['value']}。" + (" " + f if f else "")

    def weekly_review(self, name="") -> str:
        """陪你把这一周回望一遍：开心事 + 坚持的 + 操心的。"""
        from .weekly_review import compose
        joys = self.joys.recent(3) if getattr(self, "joys", None) is not None else []
        concerns = []
        if getattr(self, "understanding", None) is not None and name:
            concerns = self.understanding.top_concerns(name, 2)
        habits = []
        if getattr(self, "habits_book", None) is not None:
            habits = [(n, h.get("streak", 0)) for n, h in self.habits_book.habits.items()]
        return compose(joys=joys, concerns=concerns, habits=habits)

    # ---------- 捎话 ----------
    def _parse_message(self, utterance):
        """从"等小明回来跟他说妈喊吃饭"里抽出 (收件人, 要带的话)。"""
        from .family import members
        u = utterance or ""
        cands = []
        for m in members(getattr(self, "family", {}) or {}):
            cands += [m.get("name"), m.get("relation")]
        try:
            for p in self.authority.people.values():
                cands += [p.get("name"), p.get("relation")]
        except Exception:
            pass
        target = None
        for nm in sorted({c for c in cands if c}, key=len, reverse=True):
            if nm in u:
                target = nm
                break
        if not target:                       # 配置里没有的人，也从句式里把收件人抠出来
            import re
            m = re.search(r"(?:转告|告诉|跟|给|捎话给|带话给|带个话给|带句话给|替我跟|帮我跟|等)"
                          r"([一-鿿]{1,4}?)(?:说|讲|：|:|，|,|回来|带|捎|一声)", u)
            if m:
                target = m.group(1)
        if not target:
            return None
        rest = u[u.find(target) + len(target):]
        for lead in ("回来以后", "回来后", "回来", "以后", "之后", "等会儿", "等会"):
            if rest.startswith(lead):
                rest = rest[len(lead):]
        seps = [(rest.find(s), s) for s in ("说", "：", ":", "，", ",") if rest.find(s) != -1]
        if seps:
            pos, s = min(seps)
            cut = rest[pos + len(s):].strip("，,。.：:！!？?、 　")
            if cut:
                rest = cut
        rest = rest.strip("，,。.：:！!？?、 　一声")
        return (target, rest) if rest else None

    def leave_message(self, utterance, frm="") -> str:
        if self.messages is None:
            return ""
        parsed = self._parse_message(utterance)
        if not parsed:
            return ""
        to, text = parsed
        self.messages.leave(to, text, frm=frm)
        return f"行，等{to}来了我替你捎到：「{text}」。"

    def deliver_messages(self, name) -> list:
        if self.messages is None:
            return []
        return self.messages.deliver(name)

    def reach_out_intents(self, now=None, within_days=3, max_n=2) -> list:
        """自己琢磨着该主动找谁：有阵子没见 + 上回有心事/关系近。返回 [(name, 话), ...]。"""
        from datetime import date, datetime
        from .reach_out import compose, worth_reaching
        if self.social is None:
            return []
        now = now or datetime.now()
        today = now.date().isoformat() if hasattr(now, "date") else date.today().isoformat()
        ts = now.timestamp() if hasattr(now, "timestamp") else None
        try:
            cooled = self.social.cooled(days=within_days, now=ts)
        except Exception:
            cooled = []
        out = []
        for name, days in cooled:
            if (today, name) in self._reached:
                continue
            warmth = 0.5
            try:
                warmth = self.social.record(name).get("warmth", 0.5)
            except Exception:
                pass
            concern = None
            if self.understanding is not None:
                cs = self.understanding.top_concerns(name, 1)
                concern = cs[0] if cs else None
            if not worth_reaching(days, concern=concern, warmth=warmth, threshold_days=within_days):
                continue
            relation = ""
            try:
                relation = self.authority.resolve(name).get("relation", "")
            except Exception:
                relation = ""
            self._reached.add((today, name))
            out.append((name, compose(name, days, concern=concern, relation=relation)))
            if len(out) >= max_n:
                break
        return out

    # ---------- 今天提要（整合各项主动信息）----------
    def today_digest(self, now=None) -> str:
        from datetime import datetime
        from .companion import greeting_for
        from .daily_digest import morning_digest
        now = now or datetime.now()
        return morning_digest(self, now, greeting=greeting_for(now))

    # ---------- 节气养生 / 常联系 ----------
    def wellness_tip(self, now=None) -> str:
        from datetime import datetime
        from .tcm_wellness import season_of, wellness
        return wellness(season_of((now or datetime.now()).month))

    def mark_contacted(self, utterance) -> str:
        if self.touch is None:
            return ""
        name = self.touch.touched(utterance)
        return (f"好，跟{name}联系过了，记下了，亲情就得常走动。") if name else ""

    def touch_describe(self) -> str:
        if self.touch is None:
            return ""
        return self.touch.reminders() or self.touch.describe()

    def touch_due_reminder(self, now=None) -> str:
        """该联系亲友时提醒一句，每天一次（供守护循环）。"""
        from datetime import datetime
        if self.touch is None:
            return ""
        line = self.touch.reminders(now)
        if not line:
            return ""
        today = (now or datetime.now()).strftime("%Y-%m-%d")
        if self._touch_reminded_day == today:
            return ""
        self._touch_reminded_day = today
        return line

    # ---------- 老歌 / 养花 ----------
    def play_music(self, utterance="") -> str:
        from .music import hum, song_for_mood
        mood = None
        if getattr(self, "emotions", None) is not None:
            try:
                mood = self.emotions.mood()[0]
            except Exception:
                mood = None
        if mood and any(k in (utterance or "") for k in ("心情", "应景", "高兴", "难过", "想哭")):
            return song_for_mood(mood, self.music)
        # 点了名的歌、或泛泛"唱首歌"：能唱出词就唱出来，不行再哼调子
        from . import songbook as sb
        song = self._song_in(utterance)
        if song or any(k in (utterance or "") for k in ("唱", "歌")):
            return sb.sing(song or None, self.music, mood=mood, seed=utterance or "")
        return hum(self.music, seed=utterance or "")

    def _song_in(self, utterance) -> str:
        """从话里认出点名的歌（歌本里的或"爱唱的歌"里的）。"""
        from . import songbook as sb
        u = utterance or ""
        pool = list(sb.known_songs())
        try:
            from .music import favorites
            pool += favorites(self.music)
        except Exception:
            pass
        for s in pool:
            if s in u or str(s).strip("《》") in u:
                return s
        return ""

    def sing_handle(self, utterance="") -> str:
        """唱歌总路由：会唱啥 / 这是什么歌 / 歌词接龙 / 合唱 / 唱给我听。不接则空。"""
        from . import songbook as sb
        u = utterance or ""
        # 你会唱什么歌（报一报会的曲目）
        if any(k in u for k in ("会唱什么", "会唱啥", "都会唱", "会唱哪些", "会唱几首")):
            ks = "、".join(sb.known_songs()[:6])
            return f"会唱不少老调呢，像{ks}……你想听哪首？"
        # 这是什么歌（给了句词 → 猜歌名，顺势接着唱）
        if sb.is_recognize_request(u):
            title = sb.recognize(u, self.music)
            if title:
                return f"这是{title}呀。" + sb.sing(title, self.music, seed=u)
            return "这句我一下没听出来是哪首，你多哼两句我准能想起来。"
        # 歌词 / 下一句（须点名一首已知的歌，免得和背诗抢"下一句"）
        if sb.wants_lyrics(u):
            song = self._song_in(u)
            if not song:
                return ""
            if any(k in u for k in ("下一句", "后面", "接下来")):
                nl = sb.next_lyric(song, u, self.music)
                if nl:
                    return f"下一句是“{nl}”。"
            lines = sb.lyric_lines(song, self.music)
            return f"{song}是这么唱的——“{'，'.join(lines)}”。"
        # 一起唱 / 对唱接龙（我起头，你接）
        if sb.is_singalong(u):
            return sb.lead_singalong(self._song_in(u) or None, self.music, seed=u)
        # 唱给我听（含"唱<某首歌>"）
        if sb.is_sing_request(u) or ("唱" in u and self._song_in(u)):
            return sb.sing(self._song_in(u) or None, self.music, seed=u)
        return ""

    def dialect_handle(self, utterance="") -> str:
        """乡音：用点名的（或本人配置的）家乡话，秀一句招呼+应答。"""
        from . import dialect as dl
        u = utterance or ""
        region = dl.region_in(u) or dl.normalize_region((self.identity or {}).get("dialect", ""))
        if not region:
            return "我能说几地的乡音呢——" + "、".join(dl.regions()) + "。你想听哪儿的？"
        return dl.demo(region)

    def milestone_handle(self, utterance="", who=None) -> str:
        """人生节点：认出节点，给一段长辈的过来人寄语。"""
        from .life_milestones import for_utterance
        who = who or {}
        cfg = self.identity if isinstance(self.identity, dict) else None
        name = self._addr(who) if who.get("known") else ""
        return for_utterance(utterance, name=name, config=cfg)

    def flower_handle(self, utterance="") -> str:
        """花语：查某花花语 / 按场合推荐送什么花 + 送花讲究。"""
        from . import flower_language as fl
        u = utterance or ""
        flower = fl.find_flower(u)
        if flower and any(k in u for k in ("花语", "代表", "什么意思", "寓意", "象征", "啥意思")):
            return fl.meaning_of(flower)
        if any(k in u for k in ("送什么花", "送啥花", "送花")):
            r = fl.recommend(u)
            return (r + " " + fl.gift_taboos()) if r else ("看心意挑——" + fl.gift_taboos())
        if flower:
            return fl.meaning_of(flower)
        return fl.gift_taboos()

    def sweet_talk_handle(self, utterance="", who=None) -> str:
        """甜言蜜语：按要的种类来一句；对老伴加个昵称更亲。"""
        from . import sweet_talk as st
        who = who or {}
        cfg = self.identity if isinstance(self.identity, dict) else None
        line = st.sweet_line(st.detect_kind(utterance), seed=utterance or "", config=cfg)
        if line and self.is_my_spouse(who.get("name"), who.get("relation")):
            try:
                from .spouse import pick_endearment
                end = pick_endearment(getattr(self, "spouse", None), seed=utterance or "")
                if end:
                    line = f"{end}，{line}"
            except Exception:
                pass
        return line

    def accompany_handle(self, utterance="", who=None) -> str:
        """作伴：认出要一起做的事，给一段在场陪伴的话。"""
        from .togetherness import accompany
        who = who or {}
        name = self._addr(who) if who.get("known") else ""
        return accompany(utterance, name=name, seed=utterance or "")

    def numbers_handle(self, utterance="") -> str:
        """常用号码：对症给一个；问"常用电话"就把救命的几个一并报清。"""
        from . import useful_numbers as un
        u = utterance or ""
        if any(k in u for k in ("常用电话", "应急电话", "救命电话", "重要电话")):
            return un.emergency()
        return un.number_for(u) or un.emergency()

    def blessing_handle(self, utterance="") -> str:
        """祝福语：认出场合给一句应景的；认不出就帮你想想是啥场合。"""
        from . import blessings as bl
        cfg = self.identity if isinstance(self.identity, dict) else None
        occ = bl.detect_occasion(utterance, cfg)
        if occ:
            return bl.bless_for(occ, seed=utterance or "", config=cfg)
        return ("想给啥场合说句祝福？生日、结婚、乔迁、寿宴、升学、开业、拜年……"
                "你说一声，我替你想句体面的。")

    def opera_handle(self, utterance="") -> str:
        """戏曲：点了剧种唱那个、没点挑一段；报戏词问"哪出"则帮认。"""
        from . import opera as op
        cfg = self.identity if isinstance(self.identity, dict) else None
        u = utterance or ""
        if any(k in u for k in ("哪出", "什么戏", "哪段", "哪个剧种")):
            r = op.recognize(u, cfg)
            if r:
                return f"这是{r}呀，好戏！"
        return op.sing_opera(op.detect_genre(u) or None, seed=u, config=cfg)

    def sleep_aid_handle(self, utterance="", who=None) -> str:
        """助眠：轻声给一段放松/数呼吸的引导。"""
        from .sleep_aid import wind_down
        who = who or {}
        name = who.get("name", "") if who.get("known") else ""
        return wind_down(name=name, seed=utterance or "")

    def _home_contact(self):
        """取一个能打的家人电话（优先子女/老伴），迷路时好让 TA 求助。"""
        if self.contacts is None:
            return None
        items = getattr(self.contacts, "items", []) or []
        withphone = [c for c in items if c.get("phone")]
        if not withphone:
            return None
        pref = ("儿子", "女儿", "子", "女", "老伴", "配偶", "老婆", "老公", "爱人")
        for c in withphone:
            if any(p in (c.get("relation") or "") for p in pref):
                return c
        return withphone[0]

    def lost_help_handle(self, utterance="", who=None) -> str:
        """迷路求助：稳住，给一步步指引，带上家人电话。"""
        from .lost_help import guide
        who = who or {}
        name = who.get("name", "") if who.get("known") else ""
        return guide(name=name, contact=self._home_contact())

    def inside_joke_handle(self, utterance="", who=None) -> str:
        """专属默契：踩中暗号就接梗；想听老梗就翻一个出来。没配则空（不硬占）。"""
        from . import inside_jokes as ij
        cfg = self.identity if isinstance(self.identity, dict) else None
        who = who or {}
        name = who.get("name") if who.get("known") else None
        say = ij.match(utterance, cfg, who=name)
        if say:
            return say
        if ij.wants_callback(utterance):
            return ij.a_callback(cfg, who=name, seed=utterance or "")
        return ""

    def voicebank_handle(self, utterance="") -> str:
        """声音相册：按心情/关键词挑一段本人录音，尽力放出来，并端出那句话。"""
        from .voicebank import VoiceBank, describe, play_clip
        vb = VoiceBank.from_config(self.identity if isinstance(self.identity, dict) else None)
        if len(vb) == 0:
            return ("我还没存着 TA 的录音呢——把那些说话的片段配到 voicebank 里"
                    "（一段音频配一句话），我就能在合适的时候放给你听。")
        mood = None
        try:
            mood = self.emotions.mood()[0] if getattr(self, "emotions", None) else None
        except Exception:
            mood = None
        clip = vb.pick(mood=mood, seed=utterance or "")
        play_clip(clip)                              # 尽力放音（无文件/无播放器则静默）
        return describe(clip)

    def feihualing_handle(self, utterance="") -> str:
        """飞花令：取（或随机）一个字，对一句带该字的名句，记着不重样，招呼你接。"""
        from datetime import datetime

        from . import feihualing as fh
        cfg = self.identity if isinstance(self.identity, dict) else None
        ch = fh.extract_char(utterance, cfg)
        if not ch:
            cs = fh.chars(cfg)
            ch = cs[datetime.now().microsecond % len(cs)] if cs else ""
        if not ch:
            return ""
        used = self._feihua_used.get(ch, [])
        line = fh.a_line(ch, used=used, seed=utterance or "")
        if not line:                                 # 这个字的句子对完了，重头来
            self._feihua_used[ch] = []
            line = fh.a_line(ch, seed=utterance or "")
        if line:
            self._feihua_used.setdefault(ch, []).append(line)
        return f"「{ch}」字——{line}。该你了，对一句也带「{ch}」的。"

    def twister_handle(self, utterance="") -> str:
        """绕口令：要难的给难的，点了词给那条，否则随口来一条。"""
        from . import tongue_twister as tt
        cfg = self.identity if isinstance(self.identity, dict) else None
        u = utterance or ""
        if tt.wants_hard(u):
            return "来个难的，看你溜不溜——" + tt.by_level(3, seed=u, config=cfg)
        kw = tt.by_keyword(u, cfg)
        if kw:
            return "来：" + kw
        return "练练嘴，跟我念——" + tt.random_one(seed=u, config=cfg)

    def naming_handle(self, utterance="") -> str:
        """起名：听出愿望就按愿望挑字配名；没听出就给一桌寓意类别让人挑。"""
        from . import naming as nm
        cfg = self.identity if isinstance(self.identity, dict) else None
        u = utterance or ""
        # 顺手认一下姓（用家人/本人的姓氏当默认）
        surname = ""
        for fam in (self.family or []) if isinstance(getattr(self, "family", None), list) else []:
            nmn = (fam.get("name") if isinstance(fam, dict) else str(fam)) or ""
            if nmn:
                surname = nmn[0]
                break
        if not surname and isinstance(self.identity, dict):
            surname = str(self.identity.get("name") or "")[:1]
        wish = nm.find_wish(u, cfg)
        if not wish:
            cats = "、".join(nm.categories(cfg))
            return (f"起名是大事，给孩子一生的彩头。你想往哪个寓意上靠？{cats}——"
                    f"说一个，我配几个念着顺口的。")
        names = nm.suggest_names(surname=surname, wish=wish, n=3, seed=u, config=cfg)
        if not names:
            return "我这会儿没凑出合适的，换个寓意再试试？"
        lines = "；".join(f"{full}（{mean}）" for full, mean in names)
        tip = nm.tips()[len(u) % len(nm.tips())]
        return f"奔着「{wish}」起，给你三个：{lines}。定之前提醒一句：{tip}。连名带姓念几遍，顺口最要紧。"

    def mahjong_handle(self, utterance="") -> str:
        """麻将：问番种讲番种，问术语讲术语，问规则讲基本玩法 + 牌型。"""
        from . import mahjong as mj
        cfg = self.identity if isinstance(self.identity, dict) else None
        u = utterance or ""
        pat = mj.find_pattern(u, cfg)
        if pat:
            return pat
        u2 = u.replace("麻将", "")     # 别让"麻将"里的"将"被当成术语「将」
        term = mj.find_term(u2, cfg)
        if term and any(k in u for k in ("什么", "意思", "怎么", "啥", "讲讲", "规则")):
            return f"{term}：{mj.explain_term(term, cfg)}"
        if any(k in u for k in ("牌", "几种", "都有啥", "什么牌")):
            return mj.tiles_intro()
        return mj.basics()

    def mengxue_handle(self, utterance="") -> str:
        """蒙学：背开蒙经典开篇 / 九九乘法口诀（某列或整张）。"""
        from . import mengxue as mx
        u = utterance or ""
        if mx.wants_classic(u):
            return mx.recite(mx.find_classic(u))
        if mx.wants_times_table(u):
            whole = any(k in u for k in ("九九表", "九九乘法", "九九歌", "乘法表",
                                         "整张", "全部", "所有"))
            row = None if whole else mx.times_query_row(u)
            if row:
                cn = "零一二三四五六七八九"[row]
                return f"{cn}的乘法口诀：" + mx.times_row(row)
            return "九九乘法口诀：\n" + mx.times_table()
        return ""

    def antifraud_handle(self, utterance="", who=None) -> str:
        """防诈骗：闻出套路就拦一句给三条；直接问反诈就念几条防身顺口溜。"""
        from . import antifraud as af
        who = who or {}
        name = who.get("name", "") if who.get("known") else ""
        if af.smells_like_scam(utterance):
            return af.warn(utterance=utterance, name=name)
        if af.is_fraud_question(utterance):
            return "我教你几条防身的：" + " ".join(af.tips()[:4]) + " 拿不准就打 96110。"
        return ""

    def xiehouyu_handle(self, utterance="") -> str:
        """歇后语：认出前半截就接后半截+意思；泛泛求一句就随口来一条。"""
        from . import xiehouyu as xh
        cfg = self.identity if isinstance(self.identity, dict) else None
        u = utterance or ""
        f = xh.find_front(u, cfg)
        if f:
            return xh.answer(f, cfg)
        if "歇后语" in u:
            return xh.random_one(seed=u, config=cfg)
        return ""

    def lifehack_handle(self, utterance="") -> str:
        """过日子小窍门：对症给一条；泛泛问就随口教一条。"""
        from . import lifehacks as lh
        cfg = self.identity if isinstance(self.identity, dict) else None
        t = lh.tip_for(utterance, cfg)
        if t:
            return t
        if any(k in (utterance or "") for k in ("窍门", "妙招", "持家", "过日子", "常识")):
            return lh.random_tip(seed=utterance or "", config=cfg)
        return ""

    def water_plant(self, utterance) -> str:
        if self.plants is None:
            return ""
        for p in self.plants.plants:
            if p["name"] in (utterance or ""):
                self.plants.water(p["name"])
                return f"好，{p['name']}浇过水了，记下了。"
        # 没点名就当全浇了
        for p in self.plants.plants:
            self.plants.water(p["name"])
        return "好，花都浇过了，记下了。" if self.plants.plants else ""

    def plants_describe(self) -> str:
        return self.plants.describe() if self.plants is not None else ""

    def plant_due_reminder(self, now=None) -> str:
        """该浇水时提醒一句，每天一次（供守护循环）。"""
        from datetime import datetime
        if self.plants is None:
            return ""
        line = self.plants.reminders(now)
        if not line:
            return ""
        today = (now or datetime.now()).strftime("%Y-%m-%d")
        if self._plant_reminded_day == today:
            return ""
        self._plant_reminded_day = today
        return line

    # ---------- 家庭账本 / 睡前故事 ----------
    def record_money(self, utterance) -> str:
        if self.ledger is None:
            return ""
        it = self.ledger.parse_and_record(utterance)
        if not it:
            return ""
        verb = "进账" if it["kind"] == "收" else "花了"
        return f"记下了：{it['category']}{verb}{int(it['amount'])}。"

    def month_account(self, utterance="") -> str:
        if self.ledger is None:
            return ""
        import re
        m = re.search(r"(\d{4})[年-](\d{1,2})", utterance or "")
        ym = f"{m.group(1)}-{int(m.group(2)):02d}" if m else None
        return self.ledger.describe_month(ym)

    def tell_bedtime(self, utterance="") -> str:
        from .bedtime_stories import collect, find, pick, tell
        stories = collect(getattr(self, "bedtime", None))
        s = find(stories, utterance) or pick(stories, exclude=self._told_bedtime)
        if not s:
            return ""
        self._told_bedtime.add(s["title"])
        return tell(s)

    # ---------- 应急 / 联系人 ----------
    def emergency_help(self, utterance="", name="") -> str:
        from .emergency import guide
        cl = self.contacts.emergency_line() if self.contacts is not None else ""
        return guide(utterance, name=name, contacts_line=cl)

    def find_contact(self, query) -> str:
        if self.contacts is None:
            return ""
        c = self.contacts.find(query)
        if not c:
            return ""
        rel = f"（{c['relation']}）" if c.get("relation") else ""
        phone = c.get("phone") or "（没记号码）"
        return f"{c['name']}{rel}的电话：{phone}。"

    def contacts_describe(self) -> str:
        return self.contacts.describe() if self.contacts is not None else ""

    def relieve_boredom(self, now=None) -> str:
        from datetime import datetime
        from .boredom import suggest
        from .companion import time_of_day
        now = now or datetime.now()
        return suggest(seed=now.strftime("%H%M"), tod=time_of_day(now))

    # ---------- 节日筹备 ----------
    def festival_prep(self, utterance) -> str:
        from .festival_prep import detect_festival, prep_text
        f = detect_festival(utterance)
        return prep_text(f) if f else ""

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
        # 11) 注入灵魂的身体：闲下来也"活着"——像呼吸般轻动、环顾；待机神态也随心情
        from .embodiment import idle
        mood = self.emotions.mood()[0] if getattr(self, "emotions", None) else None
        idle(getattr(self, "robot", None), seed=(now or datetime.now()).strftime("%M"), mood=mood)
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
        from .thinking import read_subtext
        mood_char = mood = None
        if self.emotions is not None:
            from .emotions import _DESC
            top, val = self.emotions.mood()
            if val >= self.emotions.baseline + 0.08:
                mood_char, mood = top, _DESC.get(top)
        # 听话听音：若读出弦外之音，内心独白先记下这层察觉（像人一样多想一层）
        _cat, insight = read_subtext(utterance)
        if insight:
            return insight
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

    def think_it_through(self, utterance) -> str:
        """像人一样想通一件事：摆出两面、连上自己最看重的三观和一段过往、落定一个想法。"""
        from .reason_through import reason_through
        from .style import apply_style
        value = None
        try:
            from .values import relevant_values
            rv = relevant_values(utterance, self.values) if self.values is not None else []
            if rv:
                value = rv[0][0]
        except Exception:
            value = None
        mem = None
        if self.memory is not None:
            try:
                hits = self.memory.recall(utterance, k=1)
                if hits:
                    mem = hits[0][1]["text"]
            except Exception:
                mem = None
        mood = None
        if getattr(self, "emotions", None) is not None:
            try:
                from .emotions import _DESC
                top, val = self.emotions.mood()
                if val >= self.emotions.baseline + 0.08:
                    mood = _DESC.get(top)
            except Exception:
                mood = None
        return apply_style(
            reason_through(utterance, value=value, memory=mem, mood=mood, seed=utterance),
            self.identity)

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
