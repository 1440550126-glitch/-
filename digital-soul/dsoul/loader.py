"""装配工厂：读配置 + 接好各模块 -> 一个可用的 Agent。"""

from __future__ import annotations

from pathlib import Path

import yaml

from .actions import SimulationRobot
from .agent import Agent
from .appointments import AppointmentBook
from .authority import Authority
from .calendar_book import EventBook
from .contacts import ContactBook
from .curiosity import QuestionLog
from .devices import build_device_hub, build_sensor_source
from .dream import DreamLog
from .emotions import EmotionState
from .favors import FavorBook
from .goals import GoalBook
from .habit_goals import HabitBook
from .household_ledger import Ledger
from .heirloom import collect_heirlooms
from .journal import Journal
from .joys import JoyLog
from .keep_in_touch import TouchLog
from .knowledge import Knowledge
from .llm import build_router
from .mannerisms import load_mannerisms
from .medication import MedBook
from .memory import Memory
from .notes import NoteBook
from .opinions import collect_opinions
from .perception import build_perception
from .plant_care import PlantBook
from .preferences import collect_preferences
from .predict import Calibration
from .persona import Persona
from .planner import Planner, PlanBook
from .reflect import Reflector
from .remote_agents import AgentHub
from .selfnarrative import SelfLog
from .scenes import SceneBook
from .shopping import ShoppingList
from .timecapsule import CapsuleBook
from .skills import SkillRegistry
from .social import SocialLog
from .spouse import spouse_profile
from .tasks import TaskBook
from .values import load_values
from .worldmodel import WorldModel
from .triggers import TriggerBook


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def split_paragraphs(text: str) -> list[str]:
    """把文档按空行切成段落，跳过 markdown 标题行。"""
    blocks: list[str] = []
    cur: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        if s == "":
            if cur:
                blocks.append(" ".join(cur)); cur = []
        else:
            cur.append(s)
    if cur:
        blocks.append(" ".join(cur))
    return [b for b in blocks if b]


def build_agent(base_dir=None, robot=None, llm_model: str | None = None) -> Agent:
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent

    identity = _load_yaml(base / "config" / "identity.yaml")
    relationships = _load_yaml(base / "config" / "relationships.yaml")

    memory = Memory(base / "data" / "memories" / "index.json")
    if not memory.items:  # 首次运行：自动把 sources/ 里的文档灌进记忆
        _seed_memory(base, memory)

    authority = Authority(relationships)
    persona = Persona(identity)
    perception = build_perception(base / "data" / "faces", authority)
    llm_router = build_router(_load_yaml(base / "config" / "models.yaml"), model_override=llm_model)
    llm = llm_router.default
    robot = robot or SimulationRobot()
    journal = Journal(base / "data" / "journal" / "journal.jsonl")
    emotions = EmotionState()
    knowledge = Knowledge()
    skills = SkillRegistry()
    hub = AgentHub(_load_yaml(base / "config" / "agents.yaml").get("agents", {}))
    tasks = TaskBook(base / "data" / "tasks.json")
    reflector = Reflector(memory, journal, emotions=emotions, llm=llm, identity=identity,
                          authority=authority)
    planner = Planner(memory=memory, llm=llm, identity=identity)
    plan = PlanBook(base / "data" / "plan.json")
    devcfg = _load_yaml(base / "config" / "devices.yaml")
    devices = build_device_hub(devcfg)
    scenes = SceneBook(_load_yaml(base / "config" / "scenes.yaml"))
    triggers = TriggerBook(base / "data" / "triggers.json")
    family_cfg = _load_yaml(base / "config" / "family.yaml")
    _seed_family(memory, family_cfg)   # 把每位家人的专属记忆灌进库（按 member 标签）

    return Agent(identity, persona, memory, authority, perception, llm, robot, journal,
                 emotions=emotions, knowledge=knowledge, skills=skills, hub=hub, tasks=tasks,
                 reflector=reflector, planner=planner, plan=plan, devices=devices, scenes=scenes,
                 triggers=triggers, sensor_source=build_sensor_source(devcfg),
                 dreams=DreamLog(base / "data" / "dreams.json"),
                 selflog=SelfLog(base / "data" / "self.json"),
                 values=load_values(_load_yaml(base / "config" / "values.yaml"),
                                    state_path=base / "data" / "values_state.json"),
                 values_path=base / "data" / "values_state.json",
                 curiosity=QuestionLog(base / "data" / "questions.json"),
                 worldmodel=WorldModel(base / "data" / "beliefs.json"),
                 calib=Calibration(base / "data" / "calibration.json"),
                 memorial=_load_yaml(base / "config" / "memorial.yaml"),
                 llm_router=llm_router,
                 legacy=_load_yaml(base / "config" / "legacy.yaml"),
                 care=_load_yaml(base / "config" / "care.yaml"),
                 family=family_cfg,
                 calendar=EventBook(base / "data" / "calendar.json"),
                 capsules=CapsuleBook(base / "data" / "capsules.json"),
                 notes=NoteBook(base / "data" / "notes.json"),
                 recipes=_load_yaml(base / "config" / "recipes.yaml"),
                 sayings=_load_yaml(base / "config" / "sayings.yaml"),
                 social=SocialLog(base / "data" / "social.json"),
                 goals=GoalBook(base / "data" / "goals.json"),
                 shopping=ShoppingList(base / "data" / "shopping.json"),
                 mannerisms=load_mannerisms(
                     _load_yaml(base / "config" / "mannerisms.yaml"), identity),
                 heirlooms=collect_heirlooms(
                     _load_yaml(base / "config" / "heirlooms.yaml"),
                     _load_yaml(base / "config" / "legacy.yaml")),
                 health=_load_yaml(base / "config" / "health.yaml"),
                 favors=FavorBook(base / "data" / "favors.json",
                                  seed=_load_yaml(base / "config" / "favors.yaml")),
                 stories=_load_yaml(base / "config" / "stories.yaml"),
                 teachings=_load_yaml(base / "config" / "teachings.yaml"),
                 spouse=spouse_profile(_load_yaml(base / "config" / "spouse.yaml"),
                                       family_cfg, relationships),
                 preferences=collect_preferences(
                     _load_yaml(base / "config" / "preferences.yaml"), identity),
                 humor=_load_yaml(base / "config" / "humor.yaml"),
                 medications=MedBook(base / "data" / "medications.json",
                                     seed=_load_yaml(base / "config" / "medications.yaml")),
                 safety=_load_yaml(base / "config" / "safety.yaml"),
                 appointments=AppointmentBook(base / "data" / "appointments.json",
                                              seed=_load_yaml(base / "config" / "appointments.yaml")),
                 opinions=collect_opinions(
                     _load_yaml(base / "config" / "opinions.yaml"), identity),
                 joys=JoyLog(base / "data" / "joys.json"),
                 habits_book=HabitBook(base / "data" / "habit_goals.json",
                                       seed=_load_yaml(base / "config" / "habit_goals.yaml")),
                 contacts=ContactBook(base / "data" / "contacts.json",
                                      seed=_load_yaml(base / "config" / "contacts.yaml")),
                 ledger=Ledger(base / "data" / "ledger.json"),
                 bedtime=_load_yaml(base / "config" / "bedtime.yaml"),
                 music=_load_yaml(base / "config" / "music.yaml"),
                 plants=PlantBook(base / "data" / "plants.json",
                                  seed=_load_yaml(base / "config" / "plants.yaml")),
                 touch=TouchLog(base / "data" / "keep_in_touch.json",
                                seed=_load_yaml(base / "config" / "keep_in_touch.yaml")))


def _seed_memory(base: Path, memory) -> None:
    sources = base / "data" / "memories" / "sources"
    if sources.exists():
        for f in sorted(sources.glob("*")):
            if f.suffix.lower() in (".md", ".txt"):
                for para in split_paragraphs(f.read_text(encoding="utf-8")):
                    memory.add(para, source=f.name)


def _seed_family(memory, family_cfg) -> None:
    """多人合一：把每位家人的专属记忆灌进库，打上 member:<名字> 标签。

    幂等：Memory.add 按文本去重，重复启动不会堆叠。
    """
    from .family import members
    for m in members(family_cfg):
        name = m["name"]
        for mem in (m.get("memories") or []):
            memory.add(mem, source=f"family:{name}", tags=[f"member:{name}"])


def reload_agent(agent, base_dir=None):
    """运行时热重载：人格热切换后，刷新 identity/persona/authority/memory。"""
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
    identity = _load_yaml(base / "config" / "identity.yaml")
    agent.identity = identity
    agent.persona = Persona(identity)
    agent.authority = Authority(_load_yaml(base / "config" / "relationships.yaml"))
    if getattr(agent, "perception", None) is not None:
        agent.perception.authority = agent.authority
    memory = Memory(base / "data" / "memories" / "index.json")
    if not memory.items:
        _seed_memory(base, memory)
    agent.memory = memory
    return agent
