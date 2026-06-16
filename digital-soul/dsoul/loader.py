"""装配工厂：读配置 + 接好各模块 -> 一个可用的 Agent。"""

from __future__ import annotations

from pathlib import Path

import yaml

from .actions import SimulationRobot
from .agent import Agent
from .authority import Authority
from .curiosity import QuestionLog
from .devices import build_device_hub, build_sensor_source
from .dream import DreamLog
from .emotions import EmotionState
from .journal import Journal
from .knowledge import Knowledge
from .llm import LLM
from .memory import Memory
from .perception import build_perception
from .predict import Calibration
from .persona import Persona
from .planner import Planner, PlanBook
from .reflect import Reflector
from .remote_agents import AgentHub
from .selfnarrative import SelfLog
from .scenes import SceneBook
from .skills import SkillRegistry
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
    llm = LLM(model=llm_model) if llm_model else LLM()
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
                 memorial=_load_yaml(base / "config" / "memorial.yaml"))


def _seed_memory(base: Path, memory) -> None:
    sources = base / "data" / "memories" / "sources"
    if sources.exists():
        for f in sorted(sources.glob("*")):
            if f.suffix.lower() in (".md", ".txt"):
                for para in split_paragraphs(f.read_text(encoding="utf-8")):
                    memory.add(para, source=f.name)


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
