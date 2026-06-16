"""技能 / 插件市场：从一个 registry（本地文件或 URL）发现并按名安装。

registry 是一个 JSON：
{
  "skills":  [{"name","description","url"|"file"}],
  "plugins": [{"name","description","source"}]   # source = git URL 或本地路径
}

官方去中心化市场为后续目标；当前任何人都能托管自己的 registry（一个 JSON 文件即可）。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import urllib.request
from pathlib import Path

from . import sync
from .memory import _tokens


def _fetch(url: str) -> str:
    if url.startswith(("http://", "https://")):
        req = urllib.request.Request(url, headers={"User-Agent": "Mnemo/0.1"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8")
    return Path(url).expanduser().read_text(encoding="utf-8")


def load_registry(source: str) -> dict:
    return json.loads(_fetch(source))


# ---------- 签名 / 完整性 ----------
def _canonical(reg: dict) -> bytes:
    r = {k: v for k, v in reg.items() if k != "signature"}
    return json.dumps(r, ensure_ascii=False, sort_keys=True).encode("utf-8")


def sign_registry(reg: dict, key: str) -> dict:
    out = dict(reg)
    out["signature"] = sync.hmac_sign(_canonical(reg), key)
    return out


def verify_registry(reg: dict, key: str) -> bool:
    sig = reg.get("signature")
    return bool(sig) and sync.hmac_verify(_canonical(reg), sig, key)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------- 本地评分 ----------
def _ratings_db(db_path: str) -> sqlite3.Connection:
    db = sqlite3.connect(db_path)
    db.execute("CREATE TABLE IF NOT EXISTS ratings("
               "name TEXT, stars INTEGER, note TEXT, ts REAL)")
    db.commit()
    return db


def rate(db_path: str, name: str, stars: int, note: str = "") -> None:
    db = _ratings_db(db_path)
    db.execute("INSERT INTO ratings VALUES(?,?,?,?)", (name, max(1, min(5, stars)), note, time.time()))
    db.commit()
    db.close()


def ratings_summary(db_path: str) -> dict:
    db = _ratings_db(db_path)
    rows = db.execute("SELECT name, AVG(stars) a, COUNT(*) c FROM ratings GROUP BY name").fetchall()
    db.close()
    return {r[0]: {"avg": round(r[1], 1), "count": r[2]} for r in rows}


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
            src = s.get("url") or s.get("file")
            if not src:
                raise ValueError(f"技能 {name} 缺少 url/file")
            content = _fetch(src)
            if s.get("sha256") and sha256_text(content) != s["sha256"]:
                raise ValueError(f"技能 {name} 完整性校验失败：sha256 不匹配")
            skills.learn(name=name, text=content)
            return f"skill:{name}"
    for p in registry.get("plugins", []):
        if p.get("name") == name:
            if not p.get("source"):
                raise ValueError(f"插件 {name} 缺少 source")
            plugins.install(p["source"], name=name)
            return f"plugin:{name}"
    raise KeyError(f"市场中找不到：{name}")
