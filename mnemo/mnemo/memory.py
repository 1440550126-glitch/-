"""永久记忆 + 用户画像。SQLite 持久化，纯标准库。

三层记忆：
  facts     —— 长期事实 / 偏好（带重要度、使用次数、时间），可检索
  episodes  —— 每轮对话原文（永久留存，可按关键词回溯）
  profile   —— 不断进化的"你画像"（姓名/偏好/高频话题/互动统计）

检索默认走 CJK 友好的关键词打分（重要度 + 时近 + 命中 + 使用频次），
零依赖即可工作；若 provider 支持向量，可在此基础上叠加（预留 embed 接口）。
"""
from __future__ import annotations

import math
import re
import sqlite3
import time
from pathlib import Path

# 极简中文停用词（避免高频虚词污染话题/检索）
_STOP = set("的了吗呢吧啊呀和与跟还也都就是在有我你他她它们这那个吗么没不要会能可以请帮一下"
            "把被让对从向到给为以及或者而且但是因为所以如果就像这样那样什么怎么为什么")


def _tokens(text: str) -> list[str]:
    """ASCII 词 + 中文连续段的 bigram，作为检索/话题的基本单元。"""
    text = (text or "").lower()
    toks: list[str] = []
    for w in re.findall(r"[a-z0-9_]{2,}", text):
        toks.append(w)
    for run in re.findall(r"[一-鿿]+", text):
        run = "".join(c for c in run if c not in _STOP)
        if len(run) == 1:
            toks.append(run)
        for i in range(len(run) - 1):
            toks.append(run[i:i + 2])
    return toks


class Memory:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.db_path)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS facts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL UNIQUE,
                kind TEXT DEFAULT 'fact',
                importance INTEGER DEFAULT 2,
                tags TEXT DEFAULT '',
                source TEXT DEFAULT 'user',
                use_count INTEGER DEFAULT 0,
                created_at REAL,
                last_used_at REAL
            );
            CREATE TABLE IF NOT EXISTS episodes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session TEXT,
                user TEXT,
                assistant TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS profile(
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL
            );
            CREATE TABLE IF NOT EXISTS topics(
                term TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0,
                last_at REAL
            );
            """
        )
        self.db.commit()
        if not self.get_profile("first_seen"):
            self.set_profile("first_seen", str(int(time.time())))

    # ---------- facts ----------
    def add_fact(self, text: str, kind: str = "fact", importance: int = 2,
                 tags: str = "", source: str = "user") -> int:
        text = text.strip()
        if not text:
            return -1
        now = time.time()
        cur = self.db.execute("SELECT id, importance FROM facts WHERE text=?", (text,))
        row = cur.fetchone()
        if row:
            # 已存在则提升重要度并刷新时间（强化记忆）
            self.db.execute(
                "UPDATE facts SET importance=MAX(importance,?), last_used_at=? WHERE id=?",
                (importance, now, row["id"]),
            )
            self.db.commit()
            return row["id"]
        cur = self.db.execute(
            "INSERT INTO facts(text,kind,importance,tags,source,created_at,last_used_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (text, kind, importance, tags, source, now, now),
        )
        self.db.commit()
        return cur.lastrowid

    def recall(self, query: str, limit: int = 6) -> list[dict]:
        rows = self.db.execute("SELECT * FROM facts").fetchall()
        if not rows:
            return []
        q = set(_tokens(query))
        now = time.time()
        scored: list[tuple[float, sqlite3.Row]] = []
        for r in rows:
            ftoks = set(_tokens(r["text"]))
            hit = len(q & ftoks)
            age_days = max(0.0, (now - (r["created_at"] or now)) / 86400)
            recency = 1.0 / (1.0 + age_days / 14)          # 两周半衰
            score = hit * 3 + r["importance"] + recency + math.log1p(r["use_count"])
            if hit or r["importance"] >= 4:
                scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]
        ids = [r["id"] for _, r in top]
        if ids:  # 命中即强化
            self.db.executemany(
                "UPDATE facts SET use_count=use_count+1, last_used_at=? WHERE id=?",
                [(now, i) for i in ids],
            )
            self.db.commit()
        return [dict(r) for _, r in top]

    def all_facts(self, limit: int = 100) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM facts ORDER BY importance DESC, last_used_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def forget(self, fact_id: int) -> bool:
        cur = self.db.execute("DELETE FROM facts WHERE id=?", (fact_id,))
        self.db.commit()
        return cur.rowcount > 0

    # ---------- episodes ----------
    def add_episode(self, session: str, user: str, assistant: str) -> int:
        cur = self.db.execute(
            "INSERT INTO episodes(session,user,assistant,created_at) VALUES(?,?,?,?)",
            (session, user, assistant, time.time()),
        )
        self.db.commit()
        return cur.lastrowid

    def recent_episodes(self, limit: int = 6, session: str | None = None) -> list[dict]:
        if session:
            rows = self.db.execute(
                "SELECT * FROM episodes WHERE session=? ORDER BY id DESC LIMIT ?",
                (session, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ---------- profile（画像） ----------
    def set_profile(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO profile(key,value,updated_at) VALUES(?,?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, time.time()),
        )
        self.db.commit()

    def get_profile(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM profile WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def all_profile(self) -> dict:
        return {r["key"]: r["value"] for r in self.db.execute("SELECT key,value FROM profile")}

    def _bump_topics(self, text: str) -> None:
        seen = set()
        for t in _tokens(text):
            if len(t) < 2 or t in seen:
                continue
            seen.add(t)
            self.db.execute(
                "INSERT INTO topics(term,count,last_at) VALUES(?,1,?)"
                " ON CONFLICT(term) DO UPDATE SET count=count+1, last_at=excluded.last_at",
                (t, time.time()),
            )

    def top_topics(self, n: int = 8) -> list[tuple[str, int]]:
        rows = self.db.execute(
            "SELECT term,count FROM topics ORDER BY count DESC, last_at DESC LIMIT ?", (n,)
        ).fetchall()
        return [(r["term"], r["count"]) for r in rows]

    # ---------- 学习一轮对话（让它"越来越懂你"） ----------
    _PREF_PATTERNS = [
        (r"我(?:的名字)?(?:叫|是)\s*([^\s，。,.!！?？]{1,20})", "你叫{0}", 5, "identity"),
        (r"叫我\s*([^\s，。,.!！?？]{1,20})", "称呼用户为{0}", 5, "identity"),
        (r"我(?:很|超|非常)?喜欢\s*([^\s，。,.!！?？]{1,30})", "用户喜欢{0}", 4, "preference"),
        (r"我(?:很)?讨厌\s*([^\s，。,.!！?？]{1,30})", "用户讨厌{0}", 4, "preference"),
        (r"我不喜欢\s*([^\s，。,.!！?？]{1,30})", "用户不喜欢{0}", 4, "preference"),
        (r"我(?:是|在做|从事)\s*([^\s，。,.!！?？]{1,30})(?:的)?(?:工作|程序员|开发|设计)?",
         "用户职业/身份：{0}", 4, "identity"),
    ]

    def observe(self, user_text: str, assistant_text: str, session: str = "default") -> list[str]:
        """从一轮对话里抽取并固化记忆，更新画像。返回新增/强化的画像条目摘要。"""
        learned: list[str] = []
        self.add_episode(session, user_text, assistant_text)
        self._bump_topics(user_text)

        for pat, tmpl, imp, kind in self._PREF_PATTERNS:
            m = re.search(pat, user_text)
            if m:
                val = m.group(1).strip()
                if 1 <= len(val) <= 30:
                    fact = tmpl.format(val)
                    self.add_fact(fact, kind=kind, importance=imp, source="observed")
                    learned.append(fact)
                    if kind == "identity" and ("叫" in pat or "名字" in pat):
                        self.set_profile("name", val)

        # 互动统计
        cnt = int(self.get_profile("interactions", "0")) + 1
        self.set_profile("interactions", str(cnt))
        self.set_profile("last_seen", str(int(time.time())))
        self.db.commit()
        return learned

    def profile_summary(self) -> str:
        """注入到系统提示里的"我对你的了解"。越用越丰富。"""
        p = self.all_profile()
        lines: list[str] = []
        if p.get("name"):
            lines.append(f"- 称呼：{p['name']}")
        prefs = [f["text"] for f in self.all_facts(limit=8)
                 if f["kind"] in ("preference", "identity")]
        if prefs:
            lines.append("- 已知偏好/身份：" + "；".join(prefs[:6]))
        topics = [t for t, _ in self.top_topics(6) if len(t) >= 2]
        if topics:
            lines.append("- 常聊话题：" + "、".join(topics))
        if p.get("interactions"):
            lines.append(f"- 互动次数：{p['interactions']}")
        return "\n".join(lines)

    def stats(self) -> dict:
        f = self.db.execute("SELECT COUNT(*) c FROM facts").fetchone()["c"]
        e = self.db.execute("SELECT COUNT(*) c FROM episodes").fetchone()["c"]
        t = self.db.execute("SELECT COUNT(*) c FROM topics").fetchone()["c"]
        return {"facts": f, "episodes": e, "topics": t, "profile": self.all_profile()}

    def close(self) -> None:
        self.db.close()
