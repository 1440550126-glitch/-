"""Agent 核心：组装上下文 → 调模型 → 解析工具调用 → 执行 → 循环 → 固化记忆。

工具调用走通用文本协议（模型输出 ```tool {json} ``` 代码块），不依赖各家
function-calling，因此「接入任何大模型」都能用工具。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .providers import Message, Provider
from .tools import ToolContext, ToolRegistry

_FENCE = re.compile(r"```(?:tool|json)?\s*\n?(.*?)```", re.S)


def _extract_json(text: str) -> str | None:
    """从文本中提取第一个配平的 JSON 对象。"""
    start = text.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return None


def parse_tool_call(text: str):
    """返回 (name, args) 或 None。优先解析 ```tool 代码块，回退裸 JSON。"""
    fences = _FENCE.findall(text)
    candidate = fences[-1] if fences else text
    js = _extract_json(candidate)
    if not js:
        return None
    try:
        obj = json.loads(js)
    except json.JSONDecodeError:
        return None
    if isinstance(obj, dict) and isinstance(obj.get("name"), str):
        args = obj.get("args") or obj.get("arguments") or {}
        return obj["name"], args if isinstance(args, dict) else {}
    return None


@dataclass
class Agent:
    provider: Provider
    tools: ToolRegistry
    memory: object
    skills: object
    config: object
    learn: bool = True          # 子 Agent 设为 False，避免污染主画像
    _depth: int = 0             # 委派深度，防止无限递归
    last_trace: dict = field(default_factory=dict)

    def _make_subagent(self) -> "Agent":
        return Agent(self.provider, self.tools, self.memory, self.skills, self.config,
                     learn=False, _depth=self._depth + 1)

    def _system_prompt(self, user_input: str) -> str:
        parts = [self.config.get("persona", "你是 Mnemo，用户的私人 AI 伙伴。")]

        if self.memory and self.config.get("memory.enabled", True):
            prof = self.memory.profile_summary()
            if prof:
                parts.append("## 我对你的了解（持续积累）\n" + prof)
            qvec = None
            if self.config.get("memory.semantic", False):
                try:
                    embs = self.provider.embed([user_input])
                    qvec = embs[0] if embs else None
                except Exception:  # noqa: BLE001
                    qvec = None
            hits = self.memory.recall(
                user_input, limit=int(self.config.get("memory.recall_limit", 6)),
                query_vec=qvec)
            if hits:
                parts.append("## 相关长期记忆\n" + "\n".join(f"- {h['text']}" for h in hits))

        if self.skills:
            rel = self.skills.relevant(user_input, n=3)
            if rel:
                blocks = [f"### 技能：{s.name}\n{s.description}\n{s.body}" for s in rel]
                parts.append("## 可用技能（按需采用）\n" + "\n\n".join(blocks))

        parts.append(
            "## 工具使用\n"
            "需要工具时，只输出一个代码块（块内是纯 JSON，块外不要写别的）：\n"
            "```tool\n{\"name\": \"工具名\", \"args\": {\"参数\": \"值\"}}\n```\n"
            "系统会执行并把结果返回给你，你再决定下一步。\n"
            "当你已能直接回答、无需更多工具时，正常输出最终回答（不要再写 tool 代码块）。\n"
            "可用工具：\n" + self.tools.specs()
        )
        return "\n\n".join(parts)

    def _audit(self, tool: str, args: dict, result: str) -> None:
        home = getattr(self.config, "home", None)
        if not home:
            return
        try:
            import time as _t
            line = json.dumps({"ts": _t.time(), "depth": self._depth, "tool": tool,
                               "args": args, "ok": not str(result).startswith(("[错误", "[已", "[工具异常")),
                               "result": str(result)[:200]}, ensure_ascii=False)
            with open(Path(home) / "audit.log", "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def run(self, user_input: str, *, session: str = "default", max_steps: int | None = None,
            cwd: str = ".", auto_approve: bool = True,
            confirm: Callable[[str], bool] | None = None,
            on_event: Callable[[str, dict], None] | None = None) -> str:
        max_steps = max_steps or int(self.config.get("max_steps", 8))
        emit = on_event or (lambda *_: None)
        deny = tuple(self.config.get("tools.deny", []) or ())
        ctx = ToolContext(memory=self.memory, config=self.config, cwd=cwd,
                          auto_approve=auto_approve, confirm=confirm, agent=self, deny=deny)
        steps: list[dict] = []

        messages = [Message("system", self._system_prompt(user_input))]
        # 注入最近对话，保持连续性
        if self.memory:
            for ep in self.memory.recent_episodes(limit=4, session=session):
                messages.append(Message("user", ep["user"]))
                messages.append(Message("assistant", ep["assistant"]))
        messages.append(Message("user", user_input))

        temperature = float(self.config.get("temperature", 0.7))
        max_tokens = int(self.config.get("max_tokens", 2048))
        final = ""

        for step in range(max_steps):
            emit("think", {"step": step + 1})
            reply = self.provider.chat(messages, temperature=temperature, max_tokens=max_tokens)
            call = parse_tool_call(reply)
            if not call:
                final = reply
                break
            name, args = call
            emit("tool", {"name": name, "args": args})
            messages.append(Message("assistant", reply))
            result = self.tools.run(name, args, ctx)
            self._audit(name, args, result)
            emit("observation", {"name": name, "result": result})
            steps.append({"tool": name, "args": args, "result": str(result)[:500]})
            messages.append(Message("tool", result, name=name))
        else:
            # 步数耗尽，逼出一个总结
            messages.append(Message("user", "请基于以上信息，直接给出最终回答。"))
            final = self.provider.chat(messages, temperature=temperature, max_tokens=max_tokens)

        # 固化记忆 + 进化画像（子 Agent 不写，避免污染主画像）
        if self.memory and self.learn and self.config.get("memory.enabled", True):
            learned = self.memory.observe(user_input, final, session=session)
            if learned:
                emit("learned", {"items": learned})

        # 记录本次轨迹（供"自我进化技能"提炼）
        self.last_trace = {"input": user_input, "steps": steps, "final": final}
        if self.learn:
            try:
                home = getattr(self.config, "home", None)
                if home:
                    (Path(home) / "last_trace.json").write_text(
                        json.dumps(self.last_trace, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass

        emit("final", {"text": final})
        return final
