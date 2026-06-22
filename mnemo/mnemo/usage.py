"""用量与成本观测：记录每次模型调用的 token 用量，适配任何后端。

设计：
- 优先采用各家 API 真实返回的用量（provider.last_usage）；
- 拿不到时（流式 / 本地模型 / 离线）退化为本地启发式估算，并明确标注 estimated；
- 成本完全可选——仅当用户在 config.pricing.<model> 配了单价才计算，绝不硬编码
  会过期的价目表。这样 7×24 长期运行也能看清"花了多少 token / 多少钱"。

纯标准库，数据落在主 SQLite 库的 usage 表。
"""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

# CJK / 日文假名：按 ~1 token/字估算；其余文字按 ~4 字符/token
_CJK = re.compile(r"[㐀-鿿豈-﫿぀-ヿ가-힯]")


def estimate_tokens(text: str) -> int:
    """粗略 token 估算，够用于趋势/额度观测（不追求与计费完全一致）。"""
    if not text:
        return 0
    cjk = len(_CJK.findall(text))
    rest = len(text) - cjk
    return cjk + (max(1, round(rest / 4)) if rest else 0)


def price_for(config, model: str, in_tok: int, out_tok: int) -> float:
    """按 config.pricing.<model> = {"in": 每百万输入价, "out": 每百万输出价} 计费。

    支持精确匹配或前缀匹配（gpt-4o-mini-2024-… 命中 gpt-4o-mini）。未配置则返回 0。
    """
    if not config or not model:
        return 0.0
    pricing = (config.get("pricing", {}) if hasattr(config, "get") else {}) or {}
    spec = pricing.get(model)
    if spec is None:
        # 取最长匹配前缀，避免 gpt-4 抢在 gpt-4o-mini 之前命中带日期的版本名
        best_key = None
        for key in pricing:
            if model.startswith(key) and (best_key is None or len(key) > len(best_key)):
                best_key = key
        if best_key is not None:
            spec = pricing[best_key]
    if not isinstance(spec, dict):
        return 0.0
    return (in_tok / 1e6) * float(spec.get("in", 0)) + (out_tok / 1e6) * float(spec.get("out", 0))


class UsageStore:
    def __init__(self, db_path: str | Path, check_same_thread: bool = True):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), check_same_thread=check_same_thread)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS usage(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL, session TEXT, provider TEXT, model TEXT,
                in_tok INTEGER, out_tok INTEGER, estimated INTEGER, cost REAL
            )""")
        self.db.commit()

    def record(self, *, session: str, provider: str, model: str,
               in_tok: int, out_tok: int, estimated: bool, cost: float = 0.0) -> None:
        self.db.execute(
            "INSERT INTO usage(ts,session,provider,model,in_tok,out_tok,estimated,cost)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (time.time(), session, provider, model, int(in_tok), int(out_tok),
             int(bool(estimated)), float(cost)))
        self.db.commit()

    def summary(self, since: float | None = None) -> dict:
        where, params = ("WHERE ts>=?", (since,)) if since else ("", ())
        r = self.db.execute(
            f"SELECT COUNT(*) c, COALESCE(SUM(in_tok),0) i, COALESCE(SUM(out_tok),0) o,"
            f" COALESCE(SUM(cost),0) cost, COALESCE(SUM(estimated),0) est"
            f" FROM usage {where}", params).fetchone()
        return {"calls": r["c"], "in_tok": r["i"], "out_tok": r["o"],
                "cost": r["cost"], "estimated": r["est"]}

    def by_model(self, since: float | None = None) -> list[dict]:
        where, params = ("WHERE ts>=?", (since,)) if since else ("", ())
        rows = self.db.execute(
            f"SELECT model, COUNT(*) c, COALESCE(SUM(in_tok),0) i,"
            f" COALESCE(SUM(out_tok),0) o, COALESCE(SUM(cost),0) cost"
            f" FROM usage {where} GROUP BY model ORDER BY (i+o) DESC", params).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.db.close()
