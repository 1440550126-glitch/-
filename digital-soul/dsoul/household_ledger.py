"""家庭账本：随口"今天买菜花了30""领了退休金3000"，分身替你记一笔，
月底能算清这个月进了多少、出了多少、都花哪儿了。本地持久化，纯逻辑、可单测。
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

_INCOME_KW = ("领", "收", "进账", "工资", "退休金", "卖", "收入", "挣", "赚", "中奖", "报销")
_EXPENSE_KW = ("花", "买", "付", "交", "充", "支出", "给了", "请客", "打车", "看病")

# 分类关键词 → 类目
_CATS = [
    ("买菜", ("买菜", "菜钱", "蔬菜", "肉")),
    ("吃饭", ("吃饭", "下馆子", "饭钱", "外卖", "餐")),
    ("水电", ("水电", "电费", "水费", "燃气费", "物业")),
    ("医药", ("看病", "买药", "药费", "医院", "挂号")),
    ("交通", ("打车", "加油", "公交", "地铁", "车费", "油钱")),
    ("通讯", ("话费", "流量", "宽带", "网费")),
    ("人情", ("随礼", "红包", "份子")),
    ("衣物", ("衣服", "鞋", "买衣")),
]

_NUM = re.compile(r"(\d+(?:\.\d+)?)")


def _amount(text):
    m = _NUM.search(str(text or ""))
    return float(m.group(1)) if m else None


def _kind(text) -> str:
    u = str(text or "")
    if any(k in u for k in _INCOME_KW):
        return "收"
    return "支"


def _category(text) -> str:
    u = str(text or "")
    for cat, kws in _CATS:
        if any(k in u for k in kws):
            return cat
    return "其他"


def is_money_record(utterance) -> bool:
    """像不像在报一笔账：有数字 + 有收/支的词。"""
    u = utterance or ""
    return _amount(u) is not None and any(k in u for k in _INCOME_KW + _EXPENSE_KW)


class Ledger:
    def __init__(self, path) -> None:
        self.path = Path(path)
        self.items: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.items = json.loads(self.path.read_text(encoding="utf-8")).get("items", [])
            except Exception:
                self.items = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"items": self.items}, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def record(self, amount, kind="支", category="其他", note="", now=None) -> dict | None:
        try:
            amount = round(float(amount), 2)
        except (TypeError, ValueError):
            return None
        now = now or datetime.now()
        it = {"ts": now.strftime("%Y-%m-%d %H:%M"), "kind": kind,
              "amount": amount, "category": category, "note": (note or "").strip()}
        self.items.append(it)
        self._save()
        return it

    def parse_and_record(self, utterance, now=None) -> dict | None:
        """从"今天买菜花了30"里抽出金额/收支/类目，记一笔。"""
        amt = _amount(utterance)
        if amt is None:
            return None
        return self.record(amt, kind=_kind(utterance), category=_category(utterance),
                           note=str(utterance or "").strip(), now=now)

    def month_summary(self, ym=None, now=None) -> dict:
        ym = ym or (now or datetime.now()).strftime("%Y-%m")
        income = expense = 0.0
        by_cat: dict = {}
        for it in self.items:
            if not it["ts"].startswith(ym):
                continue
            if it["kind"] == "收":
                income += it["amount"]
            else:
                expense += it["amount"]
                by_cat[it["category"]] = by_cat.get(it["category"], 0.0) + it["amount"]
        return {"month": ym, "income": round(income, 2), "expense": round(expense, 2),
                "balance": round(income - expense, 2), "by_category": by_cat}

    def describe_month(self, ym=None, now=None) -> str:
        s = self.month_summary(ym, now)
        if s["income"] == 0 and s["expense"] == 0:
            return f"{s['month']} 还没记什么账。"
        top = sorted(s["by_category"].items(), key=lambda kv: -kv[1])[:3]
        tail = ("，花得最多的是：" + "、".join(f"{c}{int(a)}" for c, a in top)) if top else ""
        return (f"{s['month']}：进账 {int(s['income'])}，花掉 {int(s['expense'])}，"
                f"结余 {int(s['balance'])}{tail}。")

    def recent(self, k=5) -> list:
        return [f"{it['ts'][5:10]} {it['kind']}{int(it['amount'])} {it['category']}"
                for it in self.items[-k:]][::-1]
