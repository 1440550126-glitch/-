"""技能 / 插件市场：从一个 registry（本地文件或 URL）发现并按名安装。

registry 是一个 JSON：
{
  "skills":  [{"name","description","url"|"file"}],
  "plugins": [{"name","description","source"}]   # source = git URL 或本地路径
}

官方去中心化市场为后续目标；当前任何人都能托管自己的 registry（一个 JSON 文件即可）。
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from .memory import _tokens


def load_registry(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": "Mnemo/0.1"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.loads(Path(source).expanduser().read_text(encoding="utf-8"))


def search(registry: dict, query: str = "") -> dict:
    if not query:
        return {"skills": registry.get("skills", []), "plugins": registry.get("plugins", [])}
    q = set(_tokens(query))

    def hit(item):
        text = f"{item.get('name','')} {item.get('description','')}"
        return bool(q & set(_tokens(text))) or query.lower() in text.lower()

    return {
        "skills": [s for s in registry.get("skills", []) if hit(s)],
        "plugins": [p for p in registry.get("plugins", []) if hit(p)],
    }


def install(name: str, registry: dict, skills, plugins) -> str:
    for s in registry.get("skills", []):
        if s.get("name") == name:
            if s.get("url"):
                skills.learn(name=name, from_url=s["url"])
            elif s.get("file"):
                skills.learn(name=name, from_file=s["file"])
            else:
                raise ValueError(f"技能 {name} 缺少 url/file")
            return f"skill:{name}"
    for p in registry.get("plugins", []):
        if p.get("name") == name:
            if not p.get("source"):
                raise ValueError(f"插件 {name} 缺少 source")
            plugins.install(p["source"], name=name)
            return f"plugin:{name}"
    raise KeyError(f"市场中找不到：{name}")
