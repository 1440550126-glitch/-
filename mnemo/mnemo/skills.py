"""技能系统：技能 = 带元信息的 Markdown 指令（或插件提供的过程）。

Agent 会在系统提示中注入"与当前任务相关"的技能正文，从而即学即用。
内置技能随包发布；用户/插件技能存放在 ~/.mnemo/skills，可学习(learn)新增。
"""
from __future__ import annotations

import os
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .memory import _tokens

BUILTIN_DIR = Path(__file__).parent / "skills_builtin"


def _safe_skill_name(name: str) -> str:
    """技能名必须是单层文件名，禁止 .. / 路径分隔符 / 绝对路径，防止写出 skills 目录。"""
    if (not name or name in (".", "..") or "/" in name or "\\" in name
            or os.sep in name or (os.altsep and os.altsep in name) or os.path.isabs(name)):
        raise ValueError(f"非法技能名：{name!r}")
    return name


@dataclass
class Skill:
    name: str
    description: str
    when_to_use: str
    body: str
    path: Path | None = None
    builtin: bool = False


def _parse_skill(text: str, path: Path | None = None, builtin=False) -> Skill:
    """解析极简 frontmatter：开头 --- 包裹的 key: value，其余为正文。"""
    meta: dict[str, str] = {}
    body = text
    if text.lstrip().startswith("---"):
        _, _, rest = text.lstrip().partition("---")
        fm, sep, body = rest.partition("---")
        if sep:
            for line in fm.strip().splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip().lower()] = v.strip()
        else:
            body = text
    name = meta.get("name") or (path.stem if path else "unnamed")
    return Skill(
        name=name,
        description=meta.get("description", ""),
        when_to_use=meta.get("when_to_use", meta.get("when", "")),
        body=body.strip(),
        path=path,
        builtin=builtin,
    )


def distill_from_trace(trace: dict, provider, name: str) -> str:
    """把一次成功任务的轨迹提炼成一个可复用技能（Markdown）。

    优先让大模型撰写；离线或失败时回退到基于轨迹的启发式模板。
    """
    inp = trace.get("input", "")
    steps = trace.get("steps", [])
    final = trace.get("final", "")
    step_lines = "\n".join(
        f"- {s['tool']}({s['args']}) → {str(s['result'])[:120]}" for s in steps
    ) or "（本次未调用工具，主要靠推理）"

    text = None
    try:
        if provider is not None and getattr(provider, "name", "") != "offline":
            from .providers import Message
            instr = (
                "下面是一次成功完成的任务记录。请把它提炼成一个【可复用技能】，"
                "严格输出 Markdown：开头用 --- frontmatter 给出 name/description/when_to_use，"
                "正文用编号步骤写清做法（工具名照写）。只输出技能本身，不要解释。\n\n"
                f"任务：{inp}\n步骤：\n{step_lines}\n最终回答：{final[:300]}"
            )
            text = provider.chat([Message("user", instr)], max_tokens=800)
    except Exception:  # noqa: BLE001
        text = None

    if not text or "---" not in text:
        text = (
            f"---\nname: {name}\ndescription: 由一次「{inp[:40]}」任务自动沉淀的技能\n"
            f"when_to_use: 遇到类似「{inp[:40]}」的任务时\n---\n\n"
            f"# {name}\n\n复用以下经过验证的步骤：\n\n{step_lines}\n\n"
            f"完成后给出清晰结论。\n"
        )
    return text


class SkillRegistry:
    def __init__(self, config):
        self.config = config
        self.user_dir = Path(config.skills_dir)
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, Skill] = {}
        self.reload()

    def reload(self) -> None:
        self._skills.clear()
        for d, builtin in ((BUILTIN_DIR, True), (self.user_dir, False)):
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                try:
                    sk = _parse_skill(f.read_text(encoding="utf-8"), f, builtin)
                    self._skills[sk.name] = sk          # 用户技能覆盖同名内置
                except Exception:
                    continue

    def list(self) -> list[Skill]:
        return list(self._skills.values())

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def relevant(self, query: str, n: int = 3) -> list[Skill]:
        q = set(_tokens(query))
        scored = []
        for sk in self._skills.values():
            text = f"{sk.name} {sk.description} {sk.when_to_use}"
            score = len(q & set(_tokens(text)))
            if score:
                scored.append((score, sk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [sk for _, sk in scored[:n]]

    def add_runtime(self, skill: Skill) -> None:
        """插件在运行时注入技能（不落盘）。"""
        self._skills[skill.name] = skill

    # ---- 学习 / 管理 ----
    def learn(self, *, name: str | None = None, text: str | None = None,
              from_file: str | None = None, from_url: str | None = None) -> Skill:
        if from_url:
            req = urllib.request.Request(from_url, headers={"User-Agent": "Mnemo/0.1"})
            with urllib.request.urlopen(req, timeout=20) as r:
                text = r.read().decode("utf-8", "replace")
        elif from_file:
            text = Path(from_file).read_text(encoding="utf-8")
        if not text:
            raise ValueError("learn 需要 text/from_file/from_url 之一")
        sk = _parse_skill(text)
        if name:
            sk.name = name
        if not sk.description:
            sk.description = sk.body.splitlines()[0][:80] if sk.body else sk.name
        _safe_skill_name(sk.name)
        dest = self.user_dir / f"{sk.name}.md"
        front = (f"---\nname: {sk.name}\ndescription: {sk.description}\n"
                 f"when_to_use: {sk.when_to_use}\n---\n\n")
        dest.write_text(front + sk.body + "\n", encoding="utf-8")
        sk.path = dest
        self._skills[sk.name] = sk
        return sk

    def scaffold(self, name: str) -> Path:
        _safe_skill_name(name)
        dest = self.user_dir / f"{name}.md"
        if dest.exists():
            return dest
        dest.write_text(
            f"---\nname: {name}\ndescription: 一句话说明这个技能做什么\n"
            f"when_to_use: 什么场景下应该用它\n---\n\n"
            f"# {name}\n\n在这里写清楚步骤与注意事项，Agent 会按此执行。\n",
            encoding="utf-8",
        )
        self.reload()
        return dest

    def remove(self, name: str) -> bool:
        sk = self._skills.get(name)
        if sk and sk.path and not sk.builtin and sk.path.exists():
            sk.path.unlink()
            self.reload()
            return True
        return False
