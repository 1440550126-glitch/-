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
    """返回 (name, args) 或 None。

    仅在「显式工具围栏」或「整条响应本身就是一个 JSON 对象」时才识别为工具调用，
    避免把最终答案里举例/展示的 JSON（含 name 字段）误当成工具执行。
    """
    fences = _FENCE.findall(text)
    if fences:
        candidate = fences[-1]
    else:
        stripped = text.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            return None
        candidate = stripped
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
    usage: object = None        # UsageStore，可空；记录每次模型调用的 token 用量
    learn: bool = True          # 子 Agent 设为 False，避免污染主画像
    _depth: int = 0             # 委派深度，防止无限递归
    last_trace: dict = field(default_factory=dict)

    def _make_subagent(self) -> "Agent":
        return Agent(self.provider, self.tools, self.memory, self.skills, self.config,
                     usage=self.usage, learn=False, _depth=self._depth + 1)

    def _track_usage(self, messages, reply, session) -> None:
        """记录一次模型调用的用量：优先真实用量，否则本地估算（标注 estimated）。"""
        if not self.usage:
            return
        from .usage import estimate_tokens, price_for
        lu = getattr(self.provider, "last_usage", None)
        if lu:
            in_tok, out_tok, estimated = lu.get("in", 0), lu.get("out", 0), False
        else:
            in_tok = sum(estimate_tokens(m.content) for m in messages)
            out_tok = estimate_tokens(reply or "")
            estimated = True
        cost = price_for(self.config, self.provider.model or "", in_tok, out_tok)
        try:
            self.usage.record(session=session, provider=self.provider.name,
                              model=self.provider.model or "default", in_tok=in_tok,
                              out_tok=out_tok, estimated=estimated, cost=cost)
        except Exception:  # noqa: BLE001
            pass

    def _active_persona(self) -> str:
        active = self.config.get("persona_active")
        personas = self.config.get("personas", {}) or {}
        if active and isinstance(personas, dict) and active in personas:
            return personas[active]
        return self.config.get("persona", "你是 Mnemo，用户的私人 AI 伙伴。")

    def _system_prompt(self, user_input: str, native: bool = False,
                       session: str | None = None) -> str:
        import datetime as _dt
        parts = [self._active_persona()]
        parts.append(f"## 当前情境\n现在是 {_dt.datetime.now():%Y-%m-%d %H:%M %A}。")

        if self.memory and session:
            summ = self.memory.get_session_summary(session)
            if summ:
                parts.append("## 早前对话摘要（本会话）\n" + summ)

        if self.memory and self.config.get("memory.enabled", True):
            # 主动提醒：到点/逾期的事项，在对话中主动提起（不止靠守护进程）
            if self.config.get("memory.proactive_reminders", True):
                try:
                    due = self.memory.due_reminders()
                except Exception:  # noqa: BLE001
                    due = []
                if due:
                    parts.append("## ⏰ 到点/逾期提醒（请在回复中自然地提醒用户）\n"
                                 + "\n".join(f"- {r['text']}" for r in due[:5]))
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

        if not native:
            parts.append(
                "## 工具使用\n"
                "需要工具时，只输出一个代码块（块内是纯 JSON，块外不要写别的）：\n"
                "```tool\n{\"name\": \"工具名\", \"args\": {\"参数\": \"值\"}}\n```\n"
                "系统会执行并把结果返回给你，你再决定下一步。\n"
                "当你已能直接回答、无需更多工具时，正常输出最终回答（不要再写 tool 代码块）。\n"
                "可用工具：\n" + self.tools.specs()
            )
        return "\n\n".join(parts)

    def _tool_specs(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "parameters": t.parameters}
                for t in self.tools._tools.values()]

    def _finalize(self, user_input, final, steps, session, emit):
        """两条执行路径共用的收尾：固化记忆 + 进化画像 + 记录轨迹。"""
        if self.memory and self.learn and self.config.get("memory.enabled", True):
            learned = self.memory.observe(user_input, final, session=session)
            if learned:
                emit("learned", {"items": learned})
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

    def _stream_or_chat(self, messages, on_token, temperature, max_tokens) -> str:
        """流式获取一步回复并返回完整文本。

        按通用工具协议判断：若该步是工具调用（文本以 ``` 或 { 开头），其内容是 JSON，
        不向用户回显；只有最终答案才逐字流式输出。on_token 为 None 时退化为普通 chat。
        """
        self.provider.last_usage = None   # 防止串到上一次调用的真实用量
        if on_token is None:
            return self.provider.chat(messages, temperature=temperature, max_tokens=max_tokens)
        buf: list[str] = []
        decided: bool | None = None   # None=未定 / True=工具调用(不回显) / False=最终答案(回显)
        for chunk in self.provider.stream(messages, temperature=temperature,
                                          max_tokens=max_tokens):
            if not chunk:
                continue
            buf.append(chunk)
            if decided is None:
                head = "".join(buf).lstrip()
                if head:                       # 见到第一个非空白字符即可判定
                    decided = head[0] in ("`", "{")
                    if not decided:
                        on_token(head)         # 回显去除前导空白后的内容
            elif decided is False:
                on_token(chunk)
        return "".join(buf)

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
            on_event: Callable[[str, dict], None] | None = None,
            on_token: Callable[[str], None] | None = None) -> str:
        max_steps = max_steps or int(self.config.get("max_steps", 8))
        emit = on_event or (lambda *_: None)
        if self.config.get("native_tools", False) and self.provider.supports_tools():
            # 原生 function-calling 路径暂不支持逐字流式（工具增量为结构化分片）
            return self._run_native(user_input, session=session, max_steps=max_steps,
                                    cwd=cwd, auto_approve=auto_approve, confirm=confirm, emit=emit)
        deny = tuple(self.config.get("tools.deny", []) or ())
        ctx = ToolContext(memory=self.memory, config=self.config, cwd=cwd,
                          auto_approve=auto_approve, confirm=confirm, agent=self, deny=deny)
        steps: list[dict] = []

        messages = [Message("system", self._system_prompt(user_input, session=session))]
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
            reply = self._stream_or_chat(messages, on_token, temperature, max_tokens)
            self._track_usage(messages, reply, session)
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
            final = self._stream_or_chat(messages, on_token, temperature, max_tokens)
            self._track_usage(messages, final, session)

        return self._finalize(user_input, final, steps, session, emit)

    def _run_native(self, user_input, *, session, max_steps, cwd, auto_approve, confirm, emit):
        """原生 function-calling 执行路径（OpenAI/Anthropic 等支持的后端）。"""
        deny = tuple(self.config.get("tools.deny", []) or ())
        ctx = ToolContext(memory=self.memory, config=self.config, cwd=cwd,
                          auto_approve=auto_approve, confirm=confirm, agent=self, deny=deny)
        specs = self._tool_specs()
        steps: list[dict] = []
        messages = [Message("system", self._system_prompt(user_input, native=True, session=session))]
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
            self.provider.last_usage = None
            res = self.provider.chat_tools(messages, specs, temperature=temperature,
                                           max_tokens=max_tokens)
            self._track_usage(messages, res.get("text", ""), session)
            calls = res.get("tool_calls") or []
            if not calls:
                final = res.get("text", "")
                break
            messages.append(Message("assistant", res.get("text", ""), tool_calls=calls))
            for tc in calls:
                emit("tool", {"name": tc["name"], "args": tc["args"]})
                result = self.tools.run(tc["name"], tc["args"], ctx)
                self._audit(tc["name"], tc["args"], result)
                emit("observation", {"name": tc["name"], "result": result})
                steps.append({"tool": tc["name"], "args": tc["args"], "result": str(result)[:500]})
                messages.append(Message("tool", result, name=tc["name"], tool_call_id=tc["id"]))
        else:
            # 步数耗尽：再追问一次逼出基于已有观察的最终回答，避免丢弃全部工具结果
            messages.append(Message("user", "请基于以上信息，直接给出最终回答。"))
            self.provider.last_usage = None
            summary = self.provider.chat_tools(messages, specs, temperature=temperature,
                                               max_tokens=max_tokens)
            self._track_usage(messages, summary.get("text", ""), session)
            final = summary.get("text", "") or res.get("text", "") or "(已达最大步数)"

        return self._finalize(user_input, final, steps, session, emit)
