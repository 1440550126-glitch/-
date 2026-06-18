"""永久记忆 + 用户画像。SQLite 持久化，纯标准库。

三层记忆：
  facts     —— 长期事实 / 偏好（带重要度、使用次数、时间），可检索
  episodes  —— 每轮对话原文（永久留存，可按关键词回溯）
  profile   —— 不断进化的"你画像"（姓名/偏好/高频话题/互动统计）

检索默认走 CJK 友好的关键词打分（重要度 + 时近 + 命中 + 使用频次），
零依赖即可工作；若 provider 支持向量，可在此基础上叠加（预留 embed 接口）。
"""
from __future__ import annotations

import json
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


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def parse_when(spec: str, now: float | None = None) -> float | None:
    """把自然时间解析为 epoch：in 2h / 30m / 1d、HH:MM（今/明）、YYYY-MM-DD HH:MM。"""
    import time as _t
    from datetime import datetime, timedelta
    now = now or _t.time()
    s = (spec or "").strip().lower()
    m = re.match(r"in\s+(\d+)\s*([smhd])", s)
    if m:
        mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]
        return now + int(m.group(1)) * mult
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})[ t](\d{1,2}):(\d{2})", s)
    if m:
        y, mo, d, hh, mm = map(int, m.groups())
        try:
            return datetime(y, mo, d, hh, mm).timestamp()
        except ValueError:
            return None
    m = re.match(r"(\d{1,2}):(\d{2})$", s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if hh > 23 or mm > 59:
            return None
        dt = datetime.fromtimestamp(now).replace(hour=hh, minute=mm, second=0, microsecond=0)
        if dt.timestamp() <= now:
            dt += timedelta(days=1)
        return dt.timestamp()
    if s.isdigit():
        return float(s)
    return None


class Memory:
    def __init__(self, db_path: str | Path, check_same_thread: bool = True):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.db_path, check_same_thread=check_same_thread)
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
            CREATE TABLE IF NOT EXISTS reminders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                remind_at REAL,
                created_at REAL,
                done INTEGER DEFAULT 0
            );
            """
        )
        # 迁移：为旧库补上 embedding 列（语义检索用）
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(facts)")}
        if "embedding" not in cols:
            self.db.execute("ALTER TABLE facts ADD COLUMN embedding TEXT")
        if "lsh" not in cols:
            self.db.execute("ALTER TABLE facts ADD COLUMN lsh INTEGER")  # ANN 签名
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

    def recall(self, query: str, limit: int = 6, query_vec: list[float] | None = None) -> list[dict]:
        """关键词打分；若给出 query_vec（来自 provider.embed），叠加向量语义相似度。"""
        rows = self.db.execute("SELECT * FROM facts").fetchall()
        if not rows:
            return []
        q = set(_tokens(query))
        now = time.time()
        # ANN 预筛：只对同桶候选算余弦（大库时显著省算力）
        cands = self.ann_candidates(query_vec) if query_vec else None
        scored: list[tuple[float, sqlite3.Row]] = []
        for r in rows:
            ftoks = set(_tokens(r["text"]))
            hit = len(q & ftoks)
            age_days = max(0.0, (now - (r["created_at"] or now)) / 86400)
            recency = 1.0 / (1.0 + age_days / 14)          # 两周半衰
            score = hit * 3 + r["importance"] + recency + math.log1p(r["use_count"])
            sem_hit = False
            if query_vec and r["embedding"] and (cands is None or r["id"] in cands):
                try:
                    sim = _cosine(query_vec, json.loads(r["embedding"]))
                    score += sim * 6
                    sem_hit = sim > 0.35
                except (ValueError, TypeError):
                    pass
            if hit or sem_hit or r["importance"] >= 4:
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

    def facts_by(self, kind: str | None = None, tag: str | None = None,
                 source: str | None = None, limit: int = 100) -> list[dict]:
        """按 kind/tag/source 过滤列出事实（source 支持前缀匹配，便于按来源管理）。"""
        q = "SELECT * FROM facts WHERE 1=1"
        params: list = []
        if kind:
            q += " AND kind=?"; params.append(kind)
        if tag:
            q += " AND tags LIKE ?"; params.append(f"%{tag}%")
        if source:
            q += " AND source LIKE ?"; params.append(f"{source}%")
        q += " ORDER BY importance DESC, last_used_at DESC LIMIT ?"; params.append(limit)
        return [dict(r) for r in self.db.execute(q, params).fetchall()]

    def forget(self, fact_id: int) -> bool:
        cur = self.db.execute("DELETE FROM facts WHERE id=?", (fact_id,))
        self.db.commit()
        return cur.rowcount > 0

    def forget_by_source(self, source: str) -> int:
        """按来源批量删除（如删掉某次 ingest 的全部知识块）。前缀匹配。返回删除条数。"""
        cur = self.db.execute("DELETE FROM facts WHERE source=? OR source LIKE ?",
                              (source, f"{source}%"))
        self.db.commit()
        return cur.rowcount

    # ---------- episodes ----------
    def add_episode(self, session: str, user: str, assistant: str) -> int:
        cur = self.db.execute(
            "INSERT INTO episodes(session,user,assistant,created_at) VALUES(?,?,?,?)",
            (session, user, assistant, time.time()),
        )
        self.db.commit()
        return cur.lastrowid

    def sessions(self) -> list[dict]:
        """列出所有会话及其轮数与起止时间（最近活跃在前）。"""
        rows = self.db.execute(
            "SELECT session, COUNT(*) c, MIN(created_at) first_at, MAX(created_at) last_at"
            " FROM episodes GROUP BY session ORDER BY last_at DESC").fetchall()
        return [dict(r) for r in rows]

    def session_episodes(self, session: str, limit: int = 2000) -> list[dict]:
        """按时间顺序取某会话的全部对话（用于查看/导出）。"""
        rows = self.db.execute(
            "SELECT * FROM episodes WHERE session=? ORDER BY id LIMIT ?",
            (session, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_session_summary(self, session: str) -> str | None:
        return self.get_profile(f"summary:{session}")

    def set_session_summary(self, session: str, text: str) -> None:
        self.set_profile(f"summary:{session}", text)

    def summarize_session(self, session: str, provider, keep_recent: int = 4) -> str | None:
        """把会话中较早的对话压缩成滚动摘要，让长会话仍保持连贯（需在线 provider）。

        返回新摘要文本；不足以压缩或无 provider 能力时返回 None。
        """
        eps = self.session_episodes(session, limit=500)
        if len(eps) <= keep_recent:
            return None
        old = eps[:-keep_recent]
        prior = self.get_session_summary(session) or ""
        convo = "\n".join(f"用户：{e['user']}\n助手：{e['assistant']}" for e in old)[:6000]
        from .providers import Message
        instr = ("把以下对话压缩成简明要点摘要，保留关键事实/决定/未尽事项，中文，"
                 "作为长期上下文备忘（不超过 200 字）：\n"
                 + (f"已有摘要：\n{prior}\n\n新增对话：\n" if prior else "") + convo)
        try:
            summary = provider.chat([Message("user", instr)], max_tokens=400)
        except Exception:  # noqa: BLE001
            return None
        if summary and summary.strip():
            self.set_session_summary(session, summary.strip())
            return summary.strip()
        return None

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
    # (正则, 事实模板, 重要度, 类别, 是否作为姓名)
    _PREF_PATTERNS = [
        (r"(?:我叫|我的名字(?:是|叫)|叫我)\s*([^\s，。,.!！?？]{1,20})",
         "你叫{0}", 5, "identity", True),
        (r"我(?:很|超|非常)?喜欢\s*([^\s，。,.!！?？]{1,30})", "用户喜欢{0}", 4, "preference", False),
        (r"我(?:很)?讨厌\s*([^\s，。,.!！?？]{1,30})", "用户讨厌{0}", 4, "preference", False),
        (r"我不喜欢\s*([^\s，。,.!！?？]{1,30})", "用户不喜欢{0}", 4, "preference", False),
        (r"我(?:在做|从事|是)\s*([^\s，。,.!！?？]{1,30})", "用户职业/身份：{0}", 4, "identity", False),
    ]

    def observe(self, user_text: str, assistant_text: str, session: str = "default") -> list[str]:
        """从一轮对话里抽取并固化记忆，更新画像。返回新增/强化的画像条目摘要。"""
        learned: list[str] = []
        self.add_episode(session, user_text, assistant_text)
        self._bump_topics(user_text)

        for pat, tmpl, imp, kind, is_name in self._PREF_PATTERNS:
            m = re.search(pat, user_text)
            if m:
                val = m.group(1).strip()
                if 1 <= len(val) <= 30:
                    fact = tmpl.format(val)
                    self.add_fact(fact, kind=kind, importance=imp, source="observed")
                    learned.append(fact)
                    if is_name:
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

    # ---------- 语义记忆（向量 + LSH 近似最近邻） ----------
    def _hyperplanes(self, dim: int, n_bits: int = 16) -> list[list[float]]:
        """随机投影超平面；固定种子 → 跨运行/跨设备一致，可持久复用。"""
        key = f"lsh_{dim}"
        raw = self.get_profile(key)
        if raw:
            return json.loads(raw)
        import random
        rng = random.Random(20240607 + dim)
        planes = [[rng.gauss(0, 1) for _ in range(dim)] for _ in range(n_bits)]
        self.set_profile(key, json.dumps(planes))
        return planes

    def _signature(self, vec: list[float]) -> int:
        bits = 0
        for k, p in enumerate(self._hyperplanes(len(vec))):
            if sum(a * b for a, b in zip(vec, p)) >= 0:
                bits |= (1 << k)
        return bits

    def ann_candidates(self, query_vec: list[float], max_bits_diff: int = 5) -> set[int]:
        """LSH 多探针：按签名汉明距离筛候选，避免对全部向量做余弦。"""
        qsig = self._signature(query_vec)
        rows = self.db.execute("SELECT id, lsh FROM facts WHERE lsh IS NOT NULL").fetchall()
        return {r["id"] for r in rows
                if bin((r["lsh"] or 0) ^ qsig).count("1") <= max_bits_diff}

    def set_embedding(self, fact_id: int, vec: list[float]) -> None:
        self.db.execute("UPDATE facts SET embedding=?, lsh=? WHERE id=?",
                        (json.dumps(vec), self._signature(vec), fact_id))
        self.db.commit()

    def embed_backfill(self, provider, limit: int = 256) -> int:
        """给尚无向量的事实补算 embedding。返回新增条数。需 provider.embed 可用。"""
        rows = self.db.execute(
            "SELECT id,text FROM facts WHERE embedding IS NULL LIMIT ?", (limit,)
        ).fetchall()
        if not rows:
            return 0
        vecs = provider.embed([r["text"] for r in rows])
        if not vecs:
            return 0
        for r, v in zip(rows, vecs):
            self.set_embedding(r["id"], v)
        return len(rows)

    # ---------- 主动式记忆：巩固 / 遗忘 ----------
    def consolidate(self, max_age_days: int = 30) -> dict:
        """记忆的"睡眠巩固"：合并近重复、淡忘陈旧低价值条目。"""
        rows = self.db.execute("SELECT * FROM facts ORDER BY importance DESC, id").fetchall()
        merged, forgotten = 0, 0
        kept: list[tuple[set, int]] = []  # (tokens, id)
        now = time.time()
        for r in rows:
            toks = set(_tokens(r["text"]))
            dup_of = None
            for ktoks, kid in kept:
                inter = len(toks & ktoks)
                union = len(toks | ktoks) or 1
                if inter / union >= 0.8:          # Jaccard 近重复
                    dup_of = kid
                    break
            if dup_of is not None:
                self.db.execute("DELETE FROM facts WHERE id=?", (r["id"],))
                self.db.execute(
                    "UPDATE facts SET importance=MIN(5,importance+1) WHERE id=?", (dup_of,))
                merged += 1
                continue
            age_days = (now - (r["created_at"] or now)) / 86400
            if age_days > max_age_days and r["importance"] <= 2 and r["use_count"] == 0:
                self.db.execute("DELETE FROM facts WHERE id=?", (r["id"],))
                forgotten += 1
                continue
            kept.append((toks, r["id"]))
        self.db.commit()
        return {"merged": merged, "forgotten": forgotten, "kept": len(kept)}

    # ---------- 提醒（主动提醒） ----------
    def add_reminder(self, text: str, remind_at: float) -> int:
        cur = self.db.execute(
            "INSERT INTO reminders(text,remind_at,created_at) VALUES(?,?,?)",
            (text, remind_at, time.time()))
        self.db.commit()
        return cur.lastrowid

    def due_reminders(self, now: float | None = None) -> list[dict]:
        now = now or time.time()
        rows = self.db.execute(
            "SELECT * FROM reminders WHERE done=0 AND remind_at<=? ORDER BY remind_at",
            (now,)).fetchall()
        return [dict(r) for r in rows]

    def pending_reminders(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM reminders WHERE done=0 ORDER BY remind_at").fetchall()
        return [dict(r) for r in rows]

    def mark_reminder_done(self, rid: int) -> None:
        self.db.execute("UPDATE reminders SET done=1 WHERE id=?", (rid,))
        self.db.commit()

    # ---------- 记忆图谱 ----------
    def graph(self, limit: int = 80, min_shared: int = 2) -> dict:
        """构建记忆关系图：节点=事实，边=共享词足够多的两条事实。"""
        facts = self.all_facts(limit)
        nodes = [{"id": f["id"], "text": f["text"][:46], "kind": f["kind"],
                  "importance": f["importance"]} for f in facts]
        toks = {f["id"]: set(_tokens(f["text"])) for f in facts}
        ids = [f["id"] for f in facts]
        edges = []
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                shared = len(toks[ids[i]] & toks[ids[j]])
                if shared >= min_shared:
                    edges.append({"source": ids[i], "target": ids[j], "w": shared})
        return {"nodes": nodes, "edges": edges}

    def export_markdown(self, max_facts: int = 1000) -> str:
        """把记忆导出为人类可读的 Markdown（画像 + 事实 + 话题）。"""
        import datetime as _dt
        p = self.all_profile()
        lines = ["# Mnemo 记忆导出",
                 f"_导出时间：{_dt.datetime.now():%Y-%m-%d %H:%M}_", ""]
        prof = self.profile_summary()
        if prof:
            lines += ["## 我对你的了解", prof, ""]
        facts = self.all_facts(limit=max_facts)
        if facts:
            lines.append(f"## 事实与知识（{len(facts)}）")
            by_kind: dict[str, list] = {}
            for f in facts:
                by_kind.setdefault(f["kind"], []).append(f)
            for kind, items in sorted(by_kind.items()):
                lines.append(f"### {kind}（{len(items)}）")
                for f in items:
                    src = f" _({f['source']})_" if f.get("source") not in (None, "user") else ""
                    lines.append(f"- [重要度{f['importance']}] {f['text']}{src}")
                lines.append("")
        topics = self.top_topics(20)
        if topics:
            lines.append("## 常聊话题")
            lines.append("、".join(f"{t}({c})" for t, c in topics))
            lines.append("")
        s = self.stats()
        lines.append(f"---\n_事实 {s['facts']} · 对话 {s['episodes']} · 话题 {s['topics']}_")
        return "\n".join(lines)

    def stats(self) -> dict:
        f = self.db.execute("SELECT COUNT(*) c FROM facts").fetchone()["c"]
        e = self.db.execute("SELECT COUNT(*) c FROM episodes").fetchone()["c"]
        t = self.db.execute("SELECT COUNT(*) c FROM topics").fetchone()["c"]
        return {"facts": f, "episodes": e, "topics": t, "profile": self.all_profile()}

    def close(self) -> None:
        self.db.close()
