"""Google Gemini provider（generativelanguage API）。

原生支持文本、流式、视觉、向量与函数调用。密钥放在 x-goog-api-key 头里（不进 URL）。
也可改用 OpenAI 兼容端点（base_url=.../v1beta/openai），但原生格式更完整。
"""
from __future__ import annotations

import json

from .base import Message, Provider, ProviderError, http_post_json, http_post_sse


class GeminiProvider(Provider):
    name = "gemini"
    DEFAULT_MODEL = "gemini-2.0-flash"
    DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def _base(self) -> str:
        return self.base_url or self.DEFAULT_BASE

    def _model(self) -> str:
        return self.model or self.DEFAULT_MODEL

    def _headers(self) -> dict:
        return {"x-goog-api-key": self.api_key or ""}

    # ---- 文本路径：system→systemInstruction，tool→user 文本 ----
    @staticmethod
    def _to_contents(messages) -> tuple[dict | None, list[dict]]:
        sys_parts, contents = [], []
        for m in messages:
            if m.role == "system":
                sys_parts.append(m.content)
                continue
            if m.role == "tool":
                contents.append({"role": "user",
                                 "parts": [{"text": f"[工具 {m.name} 返回]\n{m.content}"}]})
                continue
            role = "model" if m.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        sysinstr = {"parts": [{"text": "\n\n".join(sys_parts)}]} if sys_parts else None
        return sysinstr, contents

    def _gen_config(self, temperature: float, max_tokens: int) -> dict:
        return {"temperature": temperature, "maxOutputTokens": max_tokens}

    def chat(self, messages, *, temperature=0.7, max_tokens=2048) -> str:
        if not self.api_key:
            raise ProviderError("缺少 GEMINI_API_KEY")
        sysinstr, contents = self._to_contents(messages)
        payload = {"contents": contents,
                   "generationConfig": self._gen_config(temperature, max_tokens)}
        if sysinstr:
            payload["systemInstruction"] = sysinstr
        url = f"{self._base()}/models/{self._model()}:generateContent"
        resp = http_post_json(url, payload, headers=self._headers())
        self._capture_usage(resp)
        return self._extract_text(resp)

    def stream(self, messages, *, temperature=0.7, max_tokens=2048):
        if not self.api_key:
            raise ProviderError("缺少 GEMINI_API_KEY")
        sysinstr, contents = self._to_contents(messages)
        payload = {"contents": contents,
                   "generationConfig": self._gen_config(temperature, max_tokens)}
        if sysinstr:
            payload["systemInstruction"] = sysinstr
        url = f"{self._base()}/models/{self._model()}:streamGenerateContent?alt=sse"
        for data in http_post_sse(url, payload, headers=self._headers()):
            if not data or data == "[DONE]":
                continue
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            for cand in obj.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    if part.get("text"):
                        yield part["text"]

    @staticmethod
    def _extract_text(resp: dict) -> str:
        cands = resp.get("candidates") or []
        if not cands:
            return ""
        parts = cands[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts).strip()

    def _capture_usage(self, resp: dict) -> None:
        u = resp.get("usageMetadata") or {}
        self.last_usage = ({"in": u.get("promptTokenCount", 0),
                            "out": u.get("candidatesTokenCount", 0)} if u else None)

    def available(self) -> bool:
        return bool(self.api_key)

    def supports_tools(self) -> bool:
        return bool(self.api_key)

    def supports_vision(self) -> bool:
        return bool(self.api_key)

    # ---- 视觉 ----
    def vision(self, image_path, prompt="描述这张图片") -> str:
        import base64
        import mimetypes
        from pathlib import Path
        if not self.api_key:
            raise ProviderError("缺少 GEMINI_API_KEY")
        data = base64.b64encode(Path(image_path).read_bytes()).decode()
        mime = mimetypes.guess_type(image_path)[0] or "image/png"
        payload = {"contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": mime, "data": data}},
            {"text": prompt}]}]}
        url = f"{self._base()}/models/{self._model()}:generateContent"
        resp = http_post_json(url, payload, headers=self._headers())
        return self._extract_text(resp)

    # ---- 向量 ----
    def embed(self, texts: list[str]):
        if not self.api_key:
            return None
        model = self.extra.get("embed_model", "text-embedding-004")
        payload = {"requests": [
            {"model": f"models/{model}", "content": {"parts": [{"text": t}]}}
            for t in texts]}
        url = f"{self._base()}/models/{model}:batchEmbedContents"
        try:
            resp = http_post_json(url, payload, headers=self._headers())
            return [e.get("values", []) for e in resp.get("embeddings", [])] or None
        except ProviderError:
            return None

    # ---- 原生函数调用 ----
    @staticmethod
    def _to_native(messages) -> tuple[dict | None, list[dict]]:
        sys_parts, contents = [], []
        for m in messages:
            if m.role == "system":
                sys_parts.append(m.content)
            elif m.role == "assistant" and m.tool_calls:
                parts = ([{"text": m.content}] if m.content else [])
                for tc in m.tool_calls:
                    parts.append({"functionCall": {"name": tc["name"], "args": tc["args"]}})
                contents.append({"role": "model", "parts": parts})
            elif m.role == "tool":
                contents.append({"role": "user", "parts": [
                    {"functionResponse": {"name": m.name,
                                          "response": {"result": m.content}}}]})
            else:
                role = "model" if m.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": m.content}]})
        sysinstr = {"parts": [{"text": "\n\n".join(sys_parts)}]} if sys_parts else None
        return sysinstr, contents

    def chat_tools(self, messages, tool_specs, *, temperature=0.7, max_tokens=2048) -> dict:
        if not self.api_key:
            raise ProviderError("缺少 GEMINI_API_KEY")
        sysinstr, contents = self._to_native(messages)
        decls = [{"name": s["name"], "description": s["description"],
                  "parameters": {"type": "object",
                                 "properties": {k: {"type": "string", "description": v}
                                                for k, v in s["parameters"].items()}}}
                 for s in tool_specs]
        payload = {"contents": contents,
                   "generationConfig": self._gen_config(temperature, max_tokens),
                   "tools": [{"functionDeclarations": decls}]}
        if sysinstr:
            payload["systemInstruction"] = sysinstr
        url = f"{self._base()}/models/{self._model()}:generateContent"
        resp = http_post_json(url, payload, headers=self._headers())
        self._capture_usage(resp)
        text, calls = "", []
        cands = resp.get("candidates") or []
        for part in (cands[0].get("content", {}).get("parts", []) if cands else []):
            if part.get("text"):
                text += part["text"]
            elif part.get("functionCall"):
                fc = part["functionCall"]
                calls.append({"id": fc.get("name", ""), "name": fc.get("name"),
                              "args": fc.get("args") or {}})
        return {"text": text.strip(), "tool_calls": calls}
