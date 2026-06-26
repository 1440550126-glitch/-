"""极简 Web 状态页 + 远程对话（Python 标准库，无第三方依赖）。

由 daemon.py --web 启动。手机/电脑浏览器即可：
- 实时看分身"看到谁 / 记了什么 / 聊了啥"
- 直接跟它聊天（可选择以谁的身份说话，对话同样走授权与人格）

⚠️ 它会暴露一个对话接口，请只在可信局域网使用。
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _owner(agent) -> str:
    for p in agent.authority.people.values():
        if p.get("trust") == "owner":
            return p["name"]
    return agent.identity.get("name", "我")


def _legacy_family_care(agent) -> dict:
    """数字遗产（一生/嘱托/家训）+ 多人合一（全家）+ 守护惦记，只读展示数据。

    独立成函数，便于单测；任何一块取数失败都各自降级为空，不影响整页。
    """
    chronicle = ""
    if hasattr(agent, "life_chronicle"):
        try:
            chronicle = agent.life_chronicle()
        except Exception:
            chronicle = ""
    last_words, precepts = [], []
    try:
        from .legacy import last_words as _lw, precepts as _pc
        last_words = _lw(getattr(agent, "legacy", {}) or {})
        precepts = _pc(getattr(agent, "legacy", {}) or {})
    except Exception:
        pass
    family_roster, family_members = "", []
    if getattr(agent, "family", None):
        try:
            from .family import members as _fm, roster_line as _rl
            family_roster = _rl(agent.family)
            items = getattr(agent, "memory", None).items if getattr(agent, "memory", None) else []
            for m in _fm(agent.family):
                name = m.get("name")
                tag = f"member:{name}"
                mem = sum(1 for it in items if tag in (it.get("tags") or []))
                family_members.append({"name": name, "relation": m.get("relation", ""), "mem": mem})
        except Exception:
            family_roster, family_members = "", []
    care_list = []
    if getattr(agent, "care", None):
        try:
            for person, cfg in agent.care.items():
                if not isinstance(cfg, dict):
                    continue
                meds = cfg.get("medicine")
                meds = meds if isinstance(meds, list) else ([meds] if meds else [])
                parts = []
                if meds:
                    parts.append(f"{cfg.get('note', '药')} {('、'.join(str(t) for t in meds))}")
                if cfg.get("checkup"):
                    parts.append(f"复查 {cfg.get('checkup')}")
                if parts:
                    care_list.append(f"{person}：{'；'.join(parts)}")
        except Exception:
            care_list = []
    return {"chronicle": chronicle, "last_words": last_words, "precepts": precepts,
            "family": family_roster, "family_members": family_members, "care": care_list}


def _companion_guardian(agent) -> dict:
    """陪伴守护的此刻状态（只读）：该吃的药 / 就医安排 / 习惯打卡 / 最近小确幸 / 心声。

    独立成函数便于单测；每块各自降级为空，不影响整页。
    """
    out = {"meds": [], "appts": [], "habits": [], "joys": [], "muse": "", "reasoning": [],
           "body": "", "face": "", "face_color": "", "face_emoji": ""}
    try:
        out["reasoning"] = list(getattr(agent, "_last_reasoning", []) or [])
        out["body"] = getattr(agent, "_last_body", "") or ""
        out["face"] = getattr(agent, "_last_face", "") or ""
        _mood = None
        try:
            _mood = agent.emotions.mood()[0] if getattr(agent, "emotions", None) else None
        except Exception:
            _mood = None
        if _mood:
            from .expression import emoji_for, led_color
            out["face_color"] = led_color(_mood)[1]  # 灯色十六进制
            out["face_emoji"] = emoji_for(_mood)
    except Exception:
        pass
    try:
        if getattr(agent, "medications", None) is not None:
            out["meds"] = list(agent.medications.reminders())
    except Exception:
        pass
    try:
        if getattr(agent, "appointments", None) is not None:
            out["appts"] = [f"{it['date']} {it['what']}"
                            for _, it in agent.appointments.upcoming(within=30)]
    except Exception:
        pass
    try:
        hb = getattr(agent, "habits_book", None)
        if hb is not None:
            out["habits"] = [f"{n}（连续{h.get('streak', 0)}天）" for n, h in hb.habits.items()]
    except Exception:
        pass
    try:
        if getattr(agent, "joys", None) is not None:
            out["joys"] = agent.joys.recent(3)
    except Exception:
        pass
    try:
        if hasattr(agent, "muse"):
            out["muse"] = agent.muse()
    except Exception:
        pass
    return out


def _galaxy(agent) -> dict:
    """记忆图谱 + 自生长知识库摊成力导向"星图"：人物(蓝)/话题(绿)/记忆(白)/心愿(红)/知识(金)。
    每个节点附 detail（点开看详情）。只读、容错，任一块失败各自降级。"""
    nodes, edges, seen = [], [], set()

    def clip(s, n=140):
        s = " ".join(str(s or "").split())
        return s[:n] + ("\u2026" if len(s) > n else "")

    def add(nid, label, kind, size=1, detail=""):
        if nid in seen:
            return
        seen.add(nid)
        nodes.append({"id": nid, "label": label, "kind": kind, "size": size, "detail": detail})

    try:
        all_mem = [it.get("text", "") for it in agent.memory.items]
    except Exception:
        all_mem = []

    try:
        g = agent.memory_graph()
    except Exception:
        g = None
    if g is not None:
        deg = {n: sum(w.values()) for n, w in g.adj.items()}
        for n in g.adj:
            if g.meta.get(n, {}).get("kind") == "person":
                rel = ""
                try:
                    rel = agent.authority.resolve(n).get("relation", "")
                except Exception:
                    rel = ""
                snip = [m for m in all_mem if n in m][:2]
                detail = (("我的" + rel + "。") if rel and rel not in ("陌生人", "未知") else "") + " ".join(snip)
                add(n, n, "person", 1 + deg.get(n, 0), clip(detail))
            else:
                add(n, n, "topic", 1 + deg.get(n, 0), clip(" ".join(g.mem.get(n, [])[:2])))
        eseen = set()
        for x, nb in g.adj.items():
            for y, w in nb.items():
                if x == y:
                    continue
                key = tuple(sorted((x, y)))
                if key in eseen:
                    continue
                eseen.add(key)
                edges.append({"a": x, "b": y, "w": w})
        mem_id = {}
        for n in g.adj:
            for mtext in g.mem.get(n, []):
                mid = mem_id.get(mtext)
                if mid is None:
                    mid = "mem:%d" % len(mem_id)
                    mem_id[mtext] = mid
                    add(mid, clip(mtext, 14), "memory", 1, clip(mtext))
                edges.append({"a": n, "b": mid, "w": 1})

    # 自生长 Obsidian 知识库并进同一张星图（人物/记忆按标签着色，其余算"知识"）
    try:
        vault = agent.knowledge_vault()
    except Exception:
        vault = None
    if vault is not None:
        try:
            people = set(vault.notes_with_tag("人物"))
            mems = set(vault.notes_with_tag("记忆"))
            vg = vault.graph()
            for title in list(vault.titles())[:400]:
                kind = "person" if title in people else ("memory" if title in mems else "knowledge")
                detail = ""
                try:
                    detail = clip((vault.note(title) or {}).get("body", ""))
                except Exception:
                    detail = ""
                add(title, title, kind, 1 + len(vg.get(title, ()) or ()), detail)
            tseen = set()
            for a, outs in vg.items():
                for b in (outs or ()):
                    if a != b and a in seen and b in seen:
                        key = tuple(sorted((a, b)))
                        if key in tseen:
                            continue
                        tseen.add(key)
                        edges.append({"a": a, "b": b, "w": 1})
        except Exception:
            pass

    owner = _owner(agent)
    reds = []
    try:
        reds += list((getattr(agent, "values", {}) or {}).keys())
    except Exception:
        pass
    try:
        if getattr(agent, "curiosity", None) is not None:
            reds += [q.get("q", "") for q in agent.curiosity.open()][:10]
    except Exception:
        pass
    for r in reds[:16]:
        r = str(r or "").strip()
        if not r:
            continue
        rid = "want:" + r[:10]
        add(rid, clip(r, 12), "want", 1, clip(r))
        if owner in seen:
            edges.append({"a": owner, "b": rid, "w": 1})
    return {"nodes": nodes, "edges": edges}


def _snapshot(agent, monitor) -> dict:
    present = sorted(monitor.present.keys()) if monitor is not None else []
    mems = [it["text"] for it in agent.memory.items[-8:]][::-1]
    journal, dispatches = [], []
    if agent.journal is not None:
        entries = agent.journal._all()
        journal = [
            f'{e.get("speaker", "?")}: {e.get("utterance", "")}'
            for e in entries[-8:]
        ][::-1]
        for e in entries[-16:]:
            ex = e.get("executed") or ""
            if isinstance(ex, str) and (ex.startswith("dispatch:") or ex.startswith("propose:")):
                kind, who = ex.split(":", 1)
                tag = "✅ 已派活" if kind == "dispatch" else "💡 提议"
                dispatches.append(f'{tag} → {who}：{e.get("utterance", "")}')
        dispatches = dispatches[::-1][:6]
    mood_char, mood_levels = None, {}
    if getattr(agent, "emotions", None):
        mood_levels = agent.emotions.snapshot()
        mood_char = max(mood_levels, key=mood_levels.get) if mood_levels else None
    tasks_open, tasks_done = [], 0
    if getattr(agent, "tasks", None) is not None:
        tasks_open = [
            f'{t["agent"]}：{t["instruction"]}（试 {t["attempts"]} 次）'
            for t in agent.tasks.open()
        ][::-1][:6]
        tasks_done = len(agent.tasks.done())
    reflections = agent.recent_reflections() if hasattr(agent, "recent_reflections") else []
    graph_top, graph_viz = [], {"nodes": [], "edges": []}
    if hasattr(agent, "memory_graph"):
        try:
            g = agent.memory_graph()
            graph_top = [n for n, _ in g.central(6)]
            deg = {n: sum(w.values()) for n, w in g.adj.items()}
            top = [n for n, _ in sorted(deg.items(), key=lambda x: -x[1])[:12]]
            idx = set(top)
            when_of = {it["text"]: int(it["when"]) for it in agent.memory.items
                       if str(it.get("when") or "").isdigit()}

            def _nyear(n):
                ys = [when_of[t] for t in g.mem.get(n, []) if t in when_of]
                return min(ys) if ys else None

            graph_viz["nodes"] = [
                {"id": n, "label": n, "kind": g.meta.get(n, {}).get("kind", "topic"),
                 "deg": deg[n], "year": _nyear(n)}
                for n in top]
            seen = set()
            for a in top:
                for b, w in g.adj.get(a, {}).items():
                    if b in idx and (b, a) not in seen:
                        seen.add((a, b))
                        graph_viz["edges"].append({"a": a, "b": b, "w": w})
        except Exception:
            pass
    people_names = [p["name"] for p in agent.authority.people.values() if p.get("name")]
    timeline = []
    try:
        for it in agent.memory.timeline():
            w = it.get("when")
            if w and str(w).isdigit():
                text = it["text"]
                timeline.append({"year": str(w), "text": text,
                                 "people": [n for n in people_names if n and n in text]})
    except Exception:
        timeline = []
    timeline = timeline[:40]
    tl_entities = sorted({p for e in timeline for p in e["people"]})
    fading = []
    if hasattr(agent, "fading_memories"):
        try:
            fading = [f"{t}（{int(s * 100)}%）" for s, t in agent.fading_memories(5)]
        except Exception:
            fading = []
    dreams = []
    if getattr(agent, "dreams", None) is not None:
        try:
            dreams = [{"text": r["text"], "mood": r.get("mood")} for r in agent.dreams.recent(3)]
        except Exception:
            dreams = []
    selfnar, selfhist = "", []
    if hasattr(agent, "self_narrative"):
        try:
            selfnar = agent.self_narrative()
        except Exception:
            selfnar = ""
    if getattr(agent, "selflog", None) is not None:
        try:
            selfhist = [f'{r["date"]}：{r["text"].split("。")[0]}' for r in agent.selflog.recent(5)]
        except Exception:
            selfhist = []
    thoughts = list(getattr(agent, "thoughts", []) or [])[-8:][::-1]
    anticipation = ""
    if hasattr(agent, "anticipate"):
        try:
            anticipation = agent.anticipate()
            lp = getattr(agent, "_last_prediction", None)
            if anticipation and lp:
                anticipation += f"（{int(lp['confidence'] * 100)}% · {lp['source']}）"
        except Exception:
            anticipation = ""
    curiosity_qs, worldview = [], []
    if getattr(agent, "curiosity", None) is not None:
        try:
            curiosity_qs = [q["q"] for q in agent.curiosity.open()][:5]
        except Exception:
            curiosity_qs = []
    world_shaky = []
    if getattr(agent, "worldmodel", None) is not None:
        try:
            worldview = [f"{s}（{int(c * 100)}%）" for c, s in agent.worldmodel.top(6)]
            world_shaky = [f"{s}（{int(c * 100)}%）" for c, s in agent.worldmodel.shaky(4)]
        except Exception:
            worldview, world_shaky = [], []
    if not worldview and hasattr(agent, "worldview"):
        try:
            worldview = agent.worldview()
        except Exception:
            worldview = []
    values, decisions = [], []
    if getattr(agent, "values", None):
        values = [n for n, _ in sorted(agent.values.items(),
                                       key=lambda kv: -kv[1].get("weight", 0))]
    if hasattr(agent, "recent_decisions"):
        try:
            decisions = [f'{u} → {r.split("。")[0]}' for u, r in agent.recent_decisions(4)]
        except Exception:
            decisions = []
    devices = agent.devices.rows() if getattr(agent, "devices", None) is not None else []
    scenes = agent.scenes.names() if getattr(agent, "scenes", None) is not None else []
    triggers = [t["desc"] for t in agent.triggers.all()] if getattr(agent, "triggers", None) is not None else []
    plan_items = []
    if getattr(agent, "plan", None) is not None:
        plan_items = [
            ("✅ " if it["status"] == "done" else "▢ ") + it.get("text", "")
            for it in agent.plan.items
        ][:6]
    return {
        "name": agent.identity.get("name", "我"),
        "llm": bool(agent.llm.available),
        "memory_count": len(agent.memory.items),
        "present": present,
        "recent_memories": mems,
        "recent_journal": journal,
        "dispatches": dispatches,
        "tasks_open": tasks_open,
        "tasks_done": tasks_done,
        "reflections": reflections,
        "graph": graph_top,
        "graph_viz": graph_viz,
        "galaxy": _galaxy(agent),
        "timeline": timeline,
        "timeline_entities": tl_entities,
        "fading": fading,
        "dreams": dreams,
        "self": selfnar,
        "thoughts": thoughts,
        "anticipation": anticipation,
        "curiosity": curiosity_qs,
        "worldview": worldview,
        "world_shaky": world_shaky,
        "self_history": selfhist,
        "values": values,
        "decisions": decisions,
        "plan": plan_items,
        "devices": devices,
        "scenes": scenes,
        "triggers": triggers,
        "mood": mood_char,
        "mood_levels": mood_levels,
        "people": [p["name"] for p in agent.authority.people.values()],
        "owner": _owner(agent),
        **_legacy_family_care(agent),
        "companion": _companion_guardian(agent),
    }


PAGE = r"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>数字分身</title>
<style>
:root{--bg0:#05080f;--bg1:#070b14;--card:rgba(10,18,30,.66);--line:rgba(80,200,255,.16);
  --fg:#dff3ff;--mut:#7592a8;--accent:#27e7ff;--accent2:#b14bff;--glow:#27e7ff;
  --mono:ui-monospace,"SFMono-Regular","JetBrains Mono","Cascadia Code",Consolas,monospace}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",system-ui,sans-serif;
  margin:0;color:var(--fg);-webkit-font-smoothing:antialiased;letter-spacing:.2px;position:relative;overflow-x:hidden;
  background:
    radial-gradient(1100px 620px at 50% -14%, rgba(39,231,255,.10), transparent 60%),
    radial-gradient(820px 560px at 90% 6%, rgba(177,75,255,.10), transparent 60%),
    radial-gradient(700px 600px at 6% 30%, rgba(39,231,255,.06), transparent 60%),
    linear-gradient(180deg,var(--bg1),var(--bg0));background-attachment:fixed}
body::before{content:"";position:fixed;inset:0;z-index:-2;pointer-events:none;
  background-image:linear-gradient(rgba(39,231,255,.06) 1px,transparent 1px),
    linear-gradient(90deg,rgba(39,231,255,.06) 1px,transparent 1px);background-size:44px 44px;
  -webkit-mask:radial-gradient(circle at 50% 28%,#000,transparent 78%);
  mask:radial-gradient(circle at 50% 28%,#000,transparent 78%);animation:grid 22s linear infinite}
@keyframes grid{to{background-position:0 44px,44px 0}}
body::after{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;box-shadow:inset 0 0 220px rgba(0,0,0,.7)}
.scanline{position:fixed;left:0;right:0;top:0;height:2px;z-index:60;pointer-events:none;
  background:linear-gradient(90deg,transparent,rgba(39,231,255,.55),transparent);
  box-shadow:0 0 16px rgba(39,231,255,.6);animation:sweep 7s linear infinite;opacity:.6}
@keyframes sweep{0%{transform:translateY(-4px)}100%{transform:translateY(100vh)}}
.wrap{max-width:680px;margin:0 auto;padding:18px 16px 72px;position:relative}
.card{position:relative;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:16px;margin:16px 0;
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
  box-shadow:0 0 24px rgba(39,231,255,.05),inset 0 0 22px rgba(39,231,255,.03),0 14px 34px rgba(0,0,0,.5);
  transition:box-shadow .25s,border-color .25s}
.card:hover{border-color:rgba(80,200,255,.34);
  box-shadow:0 0 30px rgba(39,231,255,.12),inset 0 0 22px rgba(39,231,255,.05),0 16px 40px rgba(0,0,0,.55)}
.card::before,.card::after{content:"";position:absolute;width:15px;height:15px;pointer-events:none;
  filter:drop-shadow(0 0 4px var(--accent))}
.card::before{top:-1px;left:-1px;border-top:2px solid var(--accent);border-left:2px solid var(--accent)}
.card::after{bottom:-1px;right:-1px;border-bottom:2px solid var(--accent);border-right:2px solid var(--accent)}
.k{color:var(--accent);font-family:var(--mono);font-size:12px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
  margin-bottom:10px;text-shadow:0 0 10px rgba(39,231,255,.4)}
.sub{color:#9fd7ec;font-family:var(--mono);font-size:11.5px;font-weight:700;letter-spacing:1px;text-transform:uppercase;
  margin:15px 0 6px;opacity:.92}
.sub::before{content:"\25b8 ";color:var(--accent2);text-shadow:0 0 8px var(--accent2)}
ul{margin:0;padding-left:18px}li{margin:4px 0;line-height:1.6}li::marker{color:var(--accent)}
.dim{color:var(--mut)}
.badge{display:inline-block;padding:3px 12px;border-radius:3px;font-size:11.5px;font-weight:800;font-family:var(--mono);
  letter-spacing:.6px;text-transform:uppercase;border:1px solid transparent}
.on{background:rgba(39,231,255,.12);color:#7ff2ff;border-color:rgba(39,231,255,.5);box-shadow:0 0 12px rgba(39,231,255,.3)}
.off{background:rgba(255,180,80,.10);color:#ffcf87;border-color:rgba(255,180,80,.4);box-shadow:0 0 12px rgba(255,180,80,.18)}
.row{display:flex;gap:8px;align-items:center;margin:8px 0;flex-wrap:wrap}
select,input,button{font:inherit;font-size:15px;padding:10px 12px;border-radius:4px;border:1px solid var(--line);
  background:rgba(6,12,22,.7);color:var(--fg);outline:none;transition:border .2s,box-shadow .2s}
input:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 1px rgba(39,231,255,.3),0 0 16px rgba(39,231,255,.2)}
input{flex:1;min-width:120px}
button{font-family:var(--mono);text-transform:uppercase;letter-spacing:.8px;font-weight:800;cursor:pointer;color:#062028;
  background:linear-gradient(180deg,#34e3ff,#16b6d6);border:1px solid rgba(120,240,255,.6);
  box-shadow:0 0 16px rgba(39,231,255,.35),inset 0 0 10px rgba(255,255,255,.18);padding:10px 16px;
  transition:transform .12s,box-shadow .2s,filter .2s}
button:hover{filter:brightness(1.1);box-shadow:0 0 26px rgba(39,231,255,.6)}button:active{transform:translateY(1px)}
.chat{max-height:300px;overflow:auto;display:flex;flex-direction:column;gap:8px;margin:10px 0;padding-right:4px}
.chat::-webkit-scrollbar{width:6px}.chat::-webkit-scrollbar-thumb{background:rgba(39,231,255,.3);border-radius:3px}
.msg{padding:9px 13px;border-radius:6px;max-width:84%;white-space:pre-wrap;word-break:break-word;line-height:1.55;animation:pop .25s ease}
@keyframes pop{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.me{align-self:flex-end;background:linear-gradient(180deg,rgba(39,231,255,.92),rgba(22,150,200,.94));color:#04141a;
  border:1px solid rgba(120,240,255,.5);border-bottom-right-radius:2px;box-shadow:0 0 16px rgba(39,231,255,.3)}
.soul{align-self:flex-start;background:rgba(177,75,255,.08);border:1px solid rgba(177,75,255,.34);
  border-bottom-left-radius:2px;box-shadow:0 0 14px rgba(177,75,255,.12)}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:2px 0 4px}
.chip{padding:7px 13px;border-radius:3px;font-size:13px;font-family:var(--mono);background:rgba(39,231,255,.06);
  border:1px solid rgba(39,231,255,.3);color:#aef0ff;cursor:pointer;transition:background .2s,box-shadow .2s,transform .1s;user-select:none}
.chip:hover{background:rgba(39,231,255,.18);box-shadow:0 0 14px rgba(39,231,255,.3)}.chip:active{transform:scale(.95)}
.barrow{display:flex;align-items:center;gap:8px;margin:4px 0}.barlab{width:24px;font-size:15px;text-align:center}
.bartrk{flex:1;height:8px;background:rgba(0,0,0,.45);border-radius:2px;overflow:hidden;border:1px solid rgba(39,231,255,.14)}
.bartrk i{display:block;height:100%;background:linear-gradient(90deg,#16b6d6,#27e7ff,#b14bff);box-shadow:0 0 10px rgba(39,231,255,.6)}
.devrow{display:flex;align-items:center;gap:8px;margin:6px 0}.devname{width:46px}
.devst{flex:1;color:var(--mut);font-size:13px;font-family:var(--mono)}
.devbtn{padding:6px 13px;font-size:13px;font-family:var(--mono);letter-spacing:.5px;text-transform:uppercase;
  background:rgba(39,231,255,.05);border:1px solid rgba(39,231,255,.28);color:#bfeaff;border-radius:3px;cursor:pointer;
  box-shadow:none;font-weight:700;transition:background .2s,box-shadow .2s}
.devbtn:hover{background:rgba(39,231,255,.16);box-shadow:0 0 12px rgba(39,231,255,.3)}
.tlyear{color:var(--accent);font-family:var(--mono);font-weight:700;margin:8px 0 2px;border-left:3px solid var(--accent);
  padding-left:8px;text-shadow:0 0 8px rgba(39,231,255,.4)}
.tlitem{color:#bcd6e6;font-size:13px;margin:2px 0 2px 16px;position:relative}
.tlitem::before{content:"\25b8";color:var(--accent);position:absolute;left:-10px}
.hero{text-align:center;position:relative;overflow:hidden;padding:26px 16px 18px}
.halo{position:absolute;left:50%;top:14px;width:250px;height:250px;transform:translateX(-50%);border-radius:50%;
  background:radial-gradient(circle,var(--glow) 0%,rgba(177,75,255,.22) 42%,transparent 64%);
  opacity:.3;filter:blur(8px);animation:halo 5s ease-in-out infinite;pointer-events:none}
@keyframes halo{0%,100%{opacity:.2;transform:translateX(-50%) scale(1)}50%{opacity:.4;transform:translateX(-50%) scale(1.1)}}
.avatar{width:148px;height:148px;margin:10px auto;border-radius:50%;position:relative;
  background:repeating-linear-gradient(rgba(0,0,0,0) 0 2px,rgba(39,231,255,.05) 2px 3px),
    radial-gradient(circle at 50% 38%,#163a4a,#0a1622);
  box-shadow:0 0 30px 3px var(--glow),inset 0 -10px 26px rgba(0,0,0,.45),inset 0 0 22px rgba(39,231,255,.15);
  animation:breathe 4.2s ease-in-out infinite;transition:box-shadow .7s,background .7s}
.avatar::before{content:"";position:absolute;inset:-16px;border-radius:50%;border:1px solid transparent;
  border-top-color:var(--accent);border-bottom-color:var(--accent2);filter:drop-shadow(0 0 6px var(--accent));
  animation:spin 7s linear infinite}
.avatar::after{content:"";position:absolute;inset:-28px;border-radius:50%;border:1px dashed rgba(177,75,255,.3);
  animation:spin 17s linear infinite reverse}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.045)}}
.avatar.talk{box-shadow:0 0 50px 12px var(--glow),inset 0 -10px 26px rgba(0,0,0,.45),inset 0 0 26px rgba(39,231,255,.25)}
.eye{position:absolute;top:56px;width:15px;height:15px;border-radius:50%;background:#eaffff;animation:blink 5.4s infinite;
  box-shadow:0 0 10px var(--glow),0 0 4px #fff;z-index:3}
.eye.l{left:46px}.eye.r{right:46px}
@keyframes blink{0%,92%,100%{transform:scaleY(1)}94%,98%{transform:scaleY(.08)}}
.mouth{position:absolute;left:50%;top:96px;width:42px;height:12px;transform:translateX(-50%);
  border-bottom:3px solid #eaffff;border-radius:0 0 22px 22px;transition:all .4s;box-shadow:0 2px 8px var(--glow);z-index:3}
.mouth.sad{border-bottom:0;border-top:3px solid #eaffff;border-radius:22px 22px 0 0;top:102px}
.mouth.flat{height:3px;background:#eaffff;border:0;border-radius:3px}
.mouth.talking{animation:talk .26s linear infinite}
@keyframes talk{0%,100%{height:6px}50%{height:20px}}
.heroname{font-size:22px;font-weight:800;margin-top:16px;letter-spacing:2px;font-family:var(--mono);
  text-shadow:0 0 14px var(--glow),0 0 30px rgba(39,231,255,.3)}
.heromood{color:#9fd7ec;font-size:14px;margin-top:5px;font-family:var(--mono);letter-spacing:.5px}
details.card>summary{cursor:pointer;list-style:none;font-weight:700;font-size:13px;color:var(--accent);font-family:var(--mono);
  letter-spacing:1.4px;text-transform:uppercase;text-shadow:0 0 8px rgba(39,231,255,.3);
  display:flex;align-items:center;justify-content:space-between}
details.card>summary::-webkit-details-marker{display:none}
details.card>summary::after{content:"\25be";color:var(--accent);transition:transform .25s}
details.card[open]>summary::after{transform:rotate(180deg)}
details.card[open]>summary{margin-bottom:10px}
::selection{background:rgba(39,231,255,.3);color:#fff}
.galaxy-full{position:fixed!important;inset:0!important;z-index:300;background:#04070e;margin:0;border-radius:0}
.galaxy-full #galaxy,.galaxy-full canvas{height:100vh!important;width:100vw!important;border-radius:0!important}
.galaxy-full #galaxyexit{display:block}
#galaxyexit{position:absolute;left:12px;top:12px;z-index:330;display:none;font-family:var(--mono);font-size:12px;
  color:var(--accent);cursor:pointer;border:1px solid rgba(39,231,255,.5);border-radius:4px;padding:5px 11px;
  background:rgba(6,14,24,.82);box-shadow:0 0 12px rgba(39,231,255,.3)}
#galaxydetail{position:absolute;right:10px;top:10px;max-width:244px;z-index:320;display:none;
  background:rgba(6,14,24,.92);border:1px solid rgba(39,231,255,.42);border-radius:6px;padding:11px 13px;
  box-shadow:0 0 22px rgba(39,231,255,.25);backdrop-filter:blur(8px)}
#galaxydetail .gd-t{font-family:var(--mono);color:var(--accent);font-weight:800;letter-spacing:.5px;
  display:flex;justify-content:space-between;gap:10px;align-items:center}
#galaxydetail .gd-x{cursor:pointer;color:var(--mut);font-weight:400}
#galaxydetail .gd-k{font-size:11px;color:var(--mut);font-family:var(--mono);margin-top:3px}
#galaxydetail .gd-b{font-size:13px;line-height:1.6;color:var(--fg);margin-top:7px;max-height:200px;overflow:auto}
</style></head>
<body>
<div class=scanline></div>
<div class=wrap>
<div class="card hero">
  <div class=halo></div>
  <div id=avatar class=avatar><div class="eye l"></div><div class="eye r"></div><div id=mouth class=mouth></div></div>
  <div id=title class=heroname>数字分身</div>
  <div id=avatarmood class=heromood>🙂 安安静静守着</div>
  <div class=row style="justify-content:center;margin-top:14px">
    <span id=llm class="badge off">…</span>
    <span id=memc class=dim style="font-size:13px">记忆 …</span>
    <button id=voicebtn class=devbtn>🔊 让 TA 出声</button>
  </div>
  <div id=present class=dim style="font-size:13px;margin-top:10px">…</div>
</div>

<div class=card>
  <div class=k>🌌 记忆星图<span id=galaxyfs style="float:right;font-family:var(--mono);font-size:11px;font-weight:700;color:var(--accent);cursor:pointer;border:1px solid rgba(39,231,255,.4);border-radius:3px;padding:2px 9px;text-shadow:0 0 8px rgba(39,231,255,.4)">⛶ 沉浸</span></div>
  <div id=galaxywrap style="position:relative">
   <canvas id=galaxy style="width:100%;height:380px;display:block;border-radius:6px;border:1px solid rgba(39,231,255,.14);background:radial-gradient(circle at 50% 42%,rgba(39,231,255,.06),transparent 70%),#04070e;cursor:grab"></canvas>
   <div id=galaxyexit onclick="galaxyFull()">✕ 退出沉浸</div>
   <div id=galaxydetail></div>
  </div>
  <div class=row style="justify-content:space-between;margin-top:8px">
    <span id=galaxylegend class=dim style="font-size:12px"></span>
    <span class=dim style="font-size:11px">拖拽/缩放 · 点开节点看详情 · 双击全屏</span>
  </div>
</div>

<div class=card>
  <div class=k>💬 跟 TA 聊聊</div>
  <div class=row><span class=dim>身份</span><select id=speaker></select></div>
  <div id=chips class=chips>
    <span class=chip onclick="ask('你今天过得怎么样')">☀️ 今天怎么样</span>
    <span class=chip onclick="ask('唱首歌')">🎵 唱首歌</span>
    <span class=chip onclick="ask('给我讲个笑话')">😄 讲个笑话</span>
    <span class=chip onclick="ask('你想我吗')">❤️ 想我吗</span>
    <span class=chip onclick="ask('来个绕口令')">👅 绕口令</span>
    <span class=chip onclick="ask('陪我聊聊')">🫶 陪我聊聊</span>
    <span class=chip onclick="ask('出个谜语')">🧩 猜谜</span>
    <span class=chip onclick="ask('简报')">📋 简报</span>
  </div>
  <div id=chat class=chat></div>
  <form id=f class=row><input id=msg placeholder="说点什么…" autocomplete=off><button>发送</button></form>
</div>

<details class=card open><summary>🫂 此刻状态</summary>
  <div class=sub>💞 心情</div><div id=mood>…</div><div id=moodbars></div>
  <div class=sub>🤖 此刻体态</div><div id=body class=dim>…</div>
  <div id=facecard><div class=sub>🙂 此刻神情 <span id=faceemoji></span></div><div id=face class=dim>…</div></div>
  <div class=sub>💭 内心独白</div><ul id=thoughts></ul>
  <div class=sub>🔮 我预感</div><div id=anticipation class=dim>…</div>
  <div class=sub>🧠 刚才怎么想的</div><ul id=reasoning></ul>
</details>

<details class=card><summary>🧠 内心世界</summary>
  <div class=sub>🪞 此刻的我</div><div id=selfnar style="font-size:14px;line-height:1.6">…</div>
  <div class=sub>💎 我珍视的</div><div id=values class=dim></div>
  <div class=sub>❓ 我好奇的</div><ul id=curiosity></ul>
  <div class=sub>🌍 我眼中的世界</div><ul id=worldview></ul>
  <div class=sub>🤔 我还拿不准的</div><ul id=worldshaky></ul>
  <div class=sub>⚖️ 抉择留痕</div><ul id=decisions></ul>
  <div class=sub>📈 成长史</div><ul id=selfhist></ul>
  <div class=sub>💡 最近的领悟</div><ul id=refl></ul>
  <div class=sub>🧠 正在淡忘</div><ul id=fading></ul>
  <div class=sub>🌙 昨夜的梦</div><div id=dreams></div>
</details>

<details class=card><summary>🫶 陪伴守护</summary>
  <div id=muse class=dim style="font-style:italic;margin-bottom:8px">…</div>
  <div class=sub>💊 该吃的药</div><ul id=meds></ul>
  <div class=sub>🏥 就医安排</div><ul id=appts></ul>
  <div class=sub>🎯 习惯打卡</div><div id=habits class=dim></div>
  <div class=sub>🌼 最近的小确幸</div><ul id=joys></ul>
  <div class=sub>🫶 守护惦记</div><ul id=care></ul>
  <div class=row style="margin-top:12px"><button id=brief>☀️ 要一份简报</button>
    <button id=diag class=devbtn>🩺 系统自检</button></div>
</details>

<details class=card><summary>🏠 家居控制</summary>
  <div class=sub>设备</div><div id=devices></div>
  <div class=sub>场景</div><div id=scenes></div>
  <div class=sub>自动化</div><ul id=triggers></ul>
  <form id=trigf class=row style="margin:6px 0"><input id=triginput placeholder="如：每天22点提醒锁门" autocomplete=off><button>添加</button></form>
  <button id=clrtrig class=devbtn>清空</button>
</details>

<details class=card><summary>👪 家人与传承</summary>
  <div class=sub>🗓️ 今天的计划</div><ul id=plan></ul>
  <div class=sub>👪 这一家子</div><div id=family class=dim></div><div id=familychips style="margin-top:6px"></div>
  <div class=sub>💌 想留给你的话</div><ul id=lastwords></ul>
  <div class=sub>📖 家训</div><ul id=precepts></ul>
  <div class=sub>🕯️ TA 的一生</div><div id=chronicle style="font-size:14px;line-height:1.7;white-space:pre-wrap">…</div>
  <div class=sub>📜 一生时间线</div><div id=tlfilters></div><div id=timeline></div>
  <div class=sub>🕸️ 关系图谱</div><div id=graph></div>
  <div class=row style="margin-top:6px"><button id=gplay class=devbtn>▶ 生长</button><input id=gyslider type=range style="flex:1"><span id=gylabel class=dim>全部</span></div>
  <div id=graphtop class=dim></div>
</details>

<details class=card><summary>🗂️ 记忆与待办</summary>
  <div class=sub>🧩 最近记住</div><ul id=mems></ul>
  <div class=sub>🕘 最近对话</div><ul id=jour></ul>
  <div class=sub>🛰️ 最近派活 / 提议</div><ul id=disp></ul>
  <div class=sub>📋 待办看板 <span id=taskstat class=dim></span></div><ul id=tasks></ul>
  <button id=retry class=devbtn style="display:none;margin-top:8px">↻ 重试全部待办</button>
</details>

<p class=dim style="text-align:center;font-size:12px">状态每 3 秒自动刷新 · /api/status 提供 JSON</p>
</div>

<script>
const $=s=>document.querySelector(s);
/* —— 记忆星图：零依赖力导向星系（星空/闪烁/全屏/详情）—— */
const GCOL={person:'#3b9bff',topic:'#2ee6a0',memory:'#d7e9ff',want:'#ff5470',knowledge:'#ffb454'};
let GX={nodes:[],edges:[],map:{},pan:{x:0,y:0},scale:1,drag:null,hot:null,sel:null,nbr:new Set(),alpha:1,t:0,stars:[],_ids:'',_raf:0};
function galaxyCenter(){const cv=$('#galaxy');return{cx:Math.max(2,cv.clientWidth)/2,cy:Math.max(2,cv.clientHeight)/2};}
function galaxyResize(){const cv=$('#galaxy');if(!cv)return;const dpr=window.devicePixelRatio||1;cv._dpr=dpr;cv.width=Math.max(2,cv.clientWidth)*dpr;cv.height=Math.max(2,cv.clientHeight)*dpr;cv._ctx=cv.getContext('2d');const W=cv.clientWidth,H=cv.clientHeight;GX.stars=[];for(let i=0;i<120;i++)GX.stars.push({x:Math.random()*W,y:Math.random()*H,r:Math.random()*1.2+.2,ph:Math.random()*6.28});}
function galaxyInit(data){const cv=$('#galaxy');if(!cv||!data)return;const ids=(data.nodes||[]).map(n=>n.id).join('|');if(ids===GX._ids&&GX.nodes.length)return;GX._ids=ids;galaxyResize();const c=galaxyCenter();GX.map={};GX.nodes=(data.nodes||[]).map(n=>{const o=Object.assign({},n,{x:c.cx+(Math.random()-0.5)*240,y:c.cy+(Math.random()-0.5)*200,vx:0,vy:0,tw:Math.random()*6.28});GX.map[n.id]=o;return o;});GX.edges=(data.edges||[]).filter(e=>GX.map[e.a]&&GX.map[e.b]);GX.alpha=1;GX.hot=null;GX.sel=null;GX.nbr=new Set();galaxyLegend();if(!GX._raf)galaxyLoop();}
function galaxyLegend(){const nm={person:'人物',topic:'话题',memory:'记忆',want:'心愿',knowledge:'知识'},c={};GX.nodes.forEach(n=>c[n.kind]=(c[n.kind]||0)+1);const el=$('#galaxylegend');if(el)el.innerHTML=Object.keys(nm).filter(k=>c[k]).map(k=>'<span style="color:'+GCOL[k]+';text-shadow:0 0 6px '+GCOL[k]+'">●</span> '+nm[k]+' '+c[k]).join('　');}
function galaxyStep(){const ns=GX.nodes,N=ns.length;if(!N)return;const c=galaxyCenter(),k=GX.alpha;for(let i=0;i<N;i++){const a=ns[i];for(let j=i+1;j<N;j++){const b=ns[j];let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+.01,d=Math.sqrt(d2),f=Math.min(42,860/d2),fx=f*dx/d,fy=f*dy/d;a.vx+=fx*k;a.vy+=fy*k;b.vx-=fx*k;b.vy-=fy*k;}a.vx+=(c.cx-a.x)*.0016*k;a.vy+=(c.cy-a.y)*.0042*k;}for(const e of GX.edges){const a=GX.map[e.a],b=GX.map[e.b];if(!a||!b)continue;let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)+.01,f=(d-48)*.02*k,fx=f*dx/d,fy=f*dy/d;a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy;}for(const a of ns){if(a===GX.drag)continue;a.vx*=.85;a.vy*=.85;a.x+=a.vx;a.y+=a.vy;}GX.alpha=Math.max(.03,GX.alpha*.996);GX.t++;}
function galaxyDraw(){const cv=$('#galaxy'),ctx=cv&&cv._ctx;if(!ctx)return;const dpr=cv._dpr||1;ctx.setTransform(dpr,0,0,dpr,0,0);const W=cv.clientWidth,H=cv.clientHeight;ctx.clearRect(0,0,W,H);for(const s of GX.stars){const tw=.35+.65*Math.abs(Math.sin(GX.t*.02+s.ph));ctx.globalAlpha=tw*.5;ctx.fillStyle='#bfe6ff';ctx.beginPath();ctx.arc(s.x,(s.y+GX.t*.12)%H,s.r,0,7);ctx.fill();}ctx.globalAlpha=1;ctx.save();ctx.translate(GX.pan.x,GX.pan.y);ctx.scale(GX.scale,GX.scale);ctx.lineWidth=.6;for(const e of GX.edges){const a=GX.map[e.a],b=GX.map[e.b];const on=GX.hot&&(e.a===GX.hot||e.b===GX.hot);ctx.strokeStyle=on?'rgba(39,231,255,.7)':'rgba(120,170,210,.10)';ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}for(const n of GX.nodes){const col=GCOL[n.kind]||'#9fb';const tw=.78+.22*Math.sin(GX.t*.05+n.tw);const r=2.4+Math.min(7,(n.size||1)*1.1);const dim=GX.hot&&n.id!==GX.hot&&!GX.nbr.has(n.id);ctx.globalAlpha=dim?.22:1;ctx.shadowColor=col;ctx.shadowBlur=(dim?2:11)*tw;ctx.fillStyle=col;ctx.beginPath();ctx.arc(n.x,n.y,r,0,7);ctx.fill();ctx.shadowBlur=0;if(n.id===GX.sel){ctx.strokeStyle='#fff';ctx.lineWidth=1.4;ctx.beginPath();ctx.arc(n.x,n.y,r+3,0,7);ctx.stroke();ctx.lineWidth=.6;}if(GX.scale>0.62&&((n.size||1)>1.6||n.kind==='person'||n.id===GX.hot)){ctx.globalAlpha=dim?.3:.92;ctx.fillStyle='#dff3ff';ctx.font='9px ui-monospace,monospace';ctx.textAlign='center';ctx.fillText(n.label,n.x,n.y-r-3);}}ctx.restore();ctx.globalAlpha=1;}
function galaxyLoop(){galaxyStep();galaxyDraw();GX._raf=requestAnimationFrame(galaxyLoop);}
function galaxyNbr(){GX.nbr=new Set();if(!GX.hot)return;for(const e of GX.edges){if(e.a===GX.hot)GX.nbr.add(e.b);if(e.b===GX.hot)GX.nbr.add(e.a);}}
function galaxyShow(n){const d=$('#galaxydetail');if(!d)return;if(!n){d.style.display='none';GX.sel=null;GX.hot=null;galaxyNbr();return;}const nm={person:'人物',topic:'话题',memory:'记忆',want:'心愿',knowledge:'知识'};d.innerHTML='<div class=gd-t><span>'+esc(n.label)+'</span><span class=gd-x onclick="galaxyShow(null)">✕</span></div><div class=gd-k>● '+(nm[n.kind]||n.kind)+'</div><div class=gd-b>'+esc(n.detail||'（暂无更多）')+'</div>';d.style.display='block';}
function galaxyFull(){const w=$('#galaxywrap');if(!w)return;const on=!w.classList.contains('galaxy-full');if(on){w._ph=document.createComment('gx');w.parentNode.insertBefore(w._ph,w);document.body.appendChild(w);w.classList.add('galaxy-full');document.body.style.overflow='hidden';}else{w.classList.remove('galaxy-full');if(w._ph&&w._ph.parentNode){w._ph.parentNode.insertBefore(w,w._ph);w._ph.remove();}document.body.style.overflow='';}const b=$('#galaxyfs');if(b)b.textContent=on?'✕ 退出':'⛶ 沉浸';setTimeout(()=>{galaxyResize();GX.alpha=Math.max(GX.alpha,.5);},40);}
(function(){const cv=$('#galaxy');if(!cv)return;function pos(ev){const r=cv.getBoundingClientRect();return{x:(ev.clientX-r.left-GX.pan.x)/GX.scale,y:(ev.clientY-r.top-GX.pan.y)/GX.scale};}function pick(p){let best=null,bd=15;for(const n of GX.nodes){const d=Math.hypot(n.x-p.x,n.y-p.y);if(d<bd){bd=d;best=n;}}return best;}let down=null;cv.addEventListener('mousedown',ev=>{const n=pick(pos(ev));down={x:ev.clientX,y:ev.clientY,moved:false,pan:{x:GX.pan.x,y:GX.pan.y}};GX.drag=n;});window.addEventListener('mousemove',ev=>{if(!down)return;const dx=ev.clientX-down.x,dy=ev.clientY-down.y;if(Math.abs(dx)+Math.abs(dy)>3)down.moved=true;if(GX.drag){const p=pos(ev);GX.drag.x=p.x;GX.drag.y=p.y;GX.drag.vx=0;GX.drag.vy=0;GX.alpha=Math.max(GX.alpha,.25);}else{GX.pan.x=down.pan.x+dx;GX.pan.y=down.pan.y+dy;}});window.addEventListener('mouseup',ev=>{if(down&&!down.moved){const n=pick(pos(ev));if(n){GX.hot=n.id;GX.sel=n.id;galaxyNbr();galaxyShow(n);if(n.kind==='person'||n.kind==='topic')setTL(n.label);}else{galaxyShow(null);}}GX.drag=null;down=null;});cv.addEventListener('dblclick',ev=>{ev.preventDefault();galaxyFull();});cv.addEventListener('wheel',ev=>{ev.preventDefault();GX.scale=Math.max(.4,Math.min(3,GX.scale*(ev.deltaY<0?1.1:.9)));},{passive:false});window.addEventListener('resize',galaxyResize);const fb=$('#galaxyfs');if(fb)fb.addEventListener('click',galaxyFull);})();

const MOODS={"喜":"😄 愉悦","怒":"😠 生气","哀":"😢 低落","惧":"😨 不安","爱":"❤️ 满心欢喜","恶":"😒 有点反感","欲":"🥺 渴望陪伴"};
const EMO={"喜":"😄","怒":"😠","哀":"😢","惧":"😨","爱":"❤️","恶":"😒","欲":"🥺"};
/* —— 让 TA 在浏览器里出声 + 那张脸跟着活 —— */
let voiceOn=false, zhVoice=null;
function pickVoice(){try{const vs=speechSynthesis.getVoices();zhVoice=vs.find(v=>/ting|sin|mei|yu|hui|chinese/i.test(v.name))||vs.find(v=>/^zh/i.test(v.lang))||null;}catch(e){}}
if('speechSynthesis' in window){try{speechSynthesis.onvoiceschanged=pickVoice;pickVoice();}catch(e){}}
function mouthTalk(on){const m=$('#mouth'),a=$('#avatar');if(m)m.classList.toggle('talking',on);if(a)a.classList.toggle('talk',on);}
function speak(t){
  if(!voiceOn||!t||!('speechSynthesis' in window))return;
  const clean=String(t).replace(/（[^）]*）/g,'').replace(/\([^)]*\)/g,'').trim();  // 去掉（舞台提示）
  if(!clean)return;
  try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(clean);
    if(zhVoice)u.voice=zhVoice; u.lang='zh-CN'; u.rate=1; u.pitch=1;
    u.onstart=()=>mouthTalk(true); u.onend=()=>mouthTalk(false); u.onerror=()=>mouthTalk(false);
    speechSynthesis.speak(u);}catch(e){}
}
function setFace(mood,color){
  if(color)document.documentElement.style.setProperty('--glow',color);  // 头像/光晕/眼睛一起染上心情色
  const m=$('#mouth'); if(m){m.className='mouth'+(mood==='哀'||mood==='惧'?' sad':(mood==='怒'||mood==='恶'?' flat':''));}
  const am=$('#avatarmood'); if(am)am.textContent=(EMO[mood]||'🙂')+' '+((MOODS[mood]||'安安静静守着').replace(/^.. /,''));
}
window.addEventListener('load',()=>{const b=$('#voicebtn');if(b)b.onclick=()=>{
  voiceOn=!voiceOn; b.textContent=voiceOn?'🔇 静音':'🔊 让 TA 出声';
  if(voiceOn){pickVoice(); speak('我在呢，咱们聊聊。');}else{try{speechSynthesis.cancel();}catch(e){} mouthTalk(false);}
};});
const SEVEN=["喜","怒","哀","惧","爱","恶","欲"];
function bars(lv){return SEVEN.map(e=>{const v=Math.max(0,Math.min(100,Math.round((lv[e]||0)*100)));return '<div class=barrow><span class=barlab title="'+e+'">'+EMO[e]+'</span><span class=bartrk><i style="width:'+v+'%"></i></span></div>';}).join('');}
function radar(lv){const S=160,c=S/2,R=54,n=SEVEN.length;function pt(i,r){const a=-Math.PI/2+2*Math.PI*i/n;return [c+r*Math.cos(a),c+r*Math.sin(a)];}let s='<svg width="170" height="160" viewBox="0 0 '+S+' '+S+'">';[0.5,1].forEach(g=>{const pts=SEVEN.map((_,i)=>pt(i,R*g).map(v=>v.toFixed(1)).join(',')).join(' ');s+='<polygon points="'+pts+'" fill="none" stroke="#2a2f3a"/>';});SEVEN.forEach((e,i)=>{const[ax,ay]=pt(i,R);s+='<line x1='+c+' y1='+c+' x2='+ax.toFixed(1)+' y2='+ay.toFixed(1)+' stroke="#2a2f3a"/>';const[lx,ly]=pt(i,R+11);s+='<text x='+lx.toFixed(1)+' y='+ly.toFixed(1)+' font-size="11" text-anchor="middle" dominant-baseline="middle">'+EMO[e]+'</text>';});const vp=SEVEN.map((e,i)=>pt(i,R*Math.max(0,Math.min(1,lv[e]||0))).map(v=>v.toFixed(1)).join(',')).join(' ');s+='<polygon points="'+vp+'" fill="#5fdd9d" fill-opacity="0.35" stroke="#5fdd9d"/>';return s+'</svg>';}
function devRow(d){const st=d.on?('开'+(d.detail?(' '+d.detail):'')):'关';return '<div class=devrow><span class=devname>'+d.label+'</span><span class=devst>'+st+'</span><button class=devbtn onclick="dev(\''+d.key+'\',\'on\')">开</button><button class=devbtn onclick="dev(\''+d.key+'\',\'off\')">关</button></div>';}
async function dev(k,a){const sp=$('#speaker').value;try{const r=await (await fetch('/api/device',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:k,action:a,speaker:sp})})).json();add(soulName,r.reply,'soul');speak(r.reply);}catch(e){}refresh();}
async function scene(n){const sp=$('#speaker').value;try{const r=await (await fetch('/api/scene',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scene:n,speaker:sp})})).json();add(soulName,r.reply,'soul');speak(r.reply);}catch(e){}refresh();}
function talkTo(name){ask('我想和'+name+'说说话');}
let inited=false, soulName="它";
function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
function renderTimeline(tl){if(!tl||!tl.length)return '<span class=dim>暂无带年份的记忆</span>';let h='',last=null;tl.forEach(e=>{if(e.year!==last){h+='<div class=tlyear>'+esc(e.year)+'</div>';last=e.year;}h+='<div class=tlitem>'+esc(e.text)+'</div>';});return h;}
const MCOL={"喜":"#e0b15f","怒":"#c0504d","哀":"#4a6fa5","惧":"#6a5a8a","爱":"#c05a7d","恶":"#5a7a5a","欲":"#7d6a4a"};
function hashStr(t){let h=0;for(let i=0;i<t.length;i++)h=(h*31+t.charCodeAt(i))&0x7fffffff;return h||1;}
function dreamArt(d){const col=MCOL[d.mood]||'#566';let h=hashStr(d.text||'');const W=300,H=64;let s='<svg width="100%" height="64" viewBox="0 0 '+W+' '+H+'" style="border-radius:8px;background:#0f1115">';for(let i=0;i<7;i++){h=(h*1103515245+12345)&0x7fffffff;const x=h%W,y=(h>>7)%H,r=8+(h>>15)%24;s+='<circle cx='+x+' cy='+y+' r='+r+' fill="'+col+'" fill-opacity="0.16"/>';}return s+'</svg>';}
function renderDreams(ds){if(!ds||!ds.length)return '<div class=dim>还没做过梦（睡一觉 / sleep 后生成）</div>';return ds.map(d=>'<div style="margin:8px 0">'+dreamArt(d)+'<div class=dim style="font-size:13px;font-style:italic;margin-top:4px">'+esc(d.text)+'</div></div>').join('');}
let tlFilter=null, _tl=[];
function setTL(e){tlFilter=e||null;gHi=tlFilter;drawTL();drawGraph();}
function drawTL(){let tl=_tl;if(tlFilter)tl=tl.filter(x=>(x.people&&x.people.includes(tlFilter))||(x.text&&x.text.indexOf(tlFilter)>=0));$('#timeline').innerHTML=renderTimeline(tl);}
function renderTLfilters(ents){let h='<button class=devbtn style="margin:2px" onclick="setTL(\'\')">全部</button>';(ents||[]).forEach(e=>h+='<button class=devbtn style="margin:2px" onclick="setTL(\''+e+'\')">'+esc(e)+'</button>');return h;}
function renderGraph(gv,maxYear,hi){if(!gv||!gv.nodes||!gv.nodes.length)return '';let nodes=gv.nodes;if(maxYear)nodes=nodes.filter(n=>!n.year||n.year<=maxYear);if(!nodes.length)return '';const ids=new Set(nodes.map(n=>n.id));const edges=(gv.edges||[]).filter(e=>ids.has(e.a)&&ids.has(e.b));const nbr=new Set();if(hi){edges.forEach(e=>{if(e.a===hi)nbr.add(e.b);if(e.b===hi)nbr.add(e.a);});}const W=320,H=290,cx=W/2,cy=H/2,R=108;const center=nodes.reduce((a,b)=>b.deg>a.deg?b:a,nodes[0]);const others=nodes.filter(x=>x!==center);const pos={};pos[center.id]={x:cx,y:cy};others.forEach((nd,i)=>{const ang=2*Math.PI*i/others.length;pos[nd.id]={x:cx+R*Math.cos(ang),y:cy+R*Math.sin(ang)};});let s='<svg width="100%" viewBox="0 0 '+W+' '+H+'">';edges.forEach(e=>{const p=pos[e.a],q=pos[e.b];if(!p||!q)return;const on=hi&&(e.a===hi||e.b===hi);const col=on?'#5fdd9d':'#2e7d32';const op=hi?(on?0.95:0.12):0.5;const wd=on?Math.min(5,e.w+1.5):Math.min(4,e.w);s+='<line x1='+p.x.toFixed(1)+' y1='+p.y.toFixed(1)+' x2='+q.x.toFixed(1)+' y2='+q.y.toFixed(1)+' stroke="'+col+'" stroke-opacity="'+op+'" stroke-width="'+wd+'"'+(on?' stroke-dasharray="2 2"':'')+'/>';});nodes.forEach(nd=>{const p=pos[nd.id],r=nd.kind==='person'?8:5,col=nd.kind==='person'?'#1565c0':'#5a3a13';const dim=hi&&nd.id!==hi&&!nbr.has(nd.id);s+='<g style="cursor:pointer" opacity="'+(dim?0.28:1)+'" onclick="setTL(\''+nd.id+'\')">';s+='<circle cx='+p.x.toFixed(1)+' cy='+p.y.toFixed(1)+' r='+(nd.id===hi?r+2:r)+' fill="'+col+'"/>';s+='<text x='+p.x.toFixed(1)+' y='+(p.y-r-3).toFixed(1)+' font-size="11" fill="#cbd5e1" text-anchor="middle">'+esc(nd.label)+'</text>';s+='</g>';});return s+'</svg>';}
let _gv={nodes:[],edges:[]},gYear=null,gHi=null,_play=null;
function gYears(gv){const ys=(gv.nodes||[]).map(n=>n.year).filter(y=>y);return ys.length?[Math.min.apply(0,ys),Math.max.apply(0,ys)]:null;}
function drawGraph(){$('#graph').innerHTML=renderGraph(_gv,gYear,gHi)||'<span class=dim>记忆还太少，画不出关系网</span>';}
function setGY(v){gYear=v?parseInt(v):null;$('#gylabel').textContent=gYear?('截至 '+gYear):'全部';drawGraph();}
function playGraph(){const r=gYears(_gv);if(!r){return;}if(_play){clearInterval(_play);_play=null;return;}let y=r[0];const sl=$('#gyslider');_play=setInterval(()=>{setGY(y);if(sl)sl.value=y;if(y>=r[1]){clearInterval(_play);_play=null;}y++;},800);}
function li(a){return a.map(x=>'<li>'+esc(x)+'</li>').join('')||'<li class=dim>—</li>';}
async function refresh(){
  try{
    const s=await (await fetch('/api/status')).json();
    soulName=s.name;
    try{galaxyInit(s.galaxy);}catch(e){}
    $('#title').textContent='🧠 '+s.name+' · 数字分身';
    $('#llm').textContent=s.llm?'大模型已接入':'大模型降级';
    $('#llm').className='badge '+(s.llm?'on':'off');
    $('#memc').textContent='记忆 '+s.memory_count+' 条';
    $('#present').textContent=s.present.length?s.present.join('、'):'暂时没看到人';
    $('#devices').innerHTML=(s.devices&&s.devices.length)?s.devices.map(devRow).join(''):'<span class=dim>无设备</span>';
    $('#scenes').innerHTML=(s.scenes&&s.scenes.length)?s.scenes.map(n=>'<button class=devbtn style="margin:3px" onclick="scene(\''+n+'\')">'+n+'</button>').join(''):'<span class=dim>无</span>';
    $('#triggers').innerHTML=li(s.triggers||[]);
    $('#thoughts').innerHTML=(s.thoughts&&s.thoughts.length)?li(s.thoughts):'<li class=dim>（还没冒出什么念头）</li>';
    $('#anticipation').textContent=s.anticipation||'还没看出规律';
    $('#curiosity').innerHTML=(s.curiosity&&s.curiosity.length)?li(s.curiosity):'<li class=dim>暂时没有想问的</li>';
    $('#worldview').innerHTML=(s.worldview&&s.worldview.length)?li(s.worldview):'<li class=dim>还在慢慢了解你的世界</li>';
    $('#worldshaky').innerHTML=(s.world_shaky&&s.world_shaky.length)?li(s.world_shaky):'<li class=dim>暂时没有动摇的判断</li>';
    $('#selfnar').textContent=s.self||'…';
    $('#selfhist').innerHTML=(s.self_history&&s.self_history.length)?li(s.self_history):'<li class=dim>还没攒下成长史（每天记一版）</li>';
    $('#values').textContent=(s.values&&s.values.length)?s.values.join(' › '):'';
    $('#decisions').innerHTML=(s.decisions&&s.decisions.length)?li(s.decisions):'<li class=dim>还没帮你做过抉择</li>';
    $('#mood').textContent=s.mood?(MOODS[s.mood]||s.mood):'平静';
    $('#moodbars').innerHTML=s.mood_levels?radar(s.mood_levels):'';
    $('#disp').innerHTML=li(s.dispatches||[]);
    const op=s.tasks_open||[];
    $('#taskstat').textContent='· 欠 '+op.length+' 件 · 已办成 '+(s.tasks_done||0)+' 件';
    $('#tasks').innerHTML=op.length?li(op):'<li class=dim>都办妥啦 🎉</li>';
    $('#retry').style.display=op.length?'inline-block':'none';
    $('#plan').innerHTML=li(s.plan||[]);
    $('#refl').innerHTML=li(s.reflections||[]);
    $('#fading').innerHTML=(s.fading&&s.fading.length)?li(s.fading):'<li class=dim>记忆都还清晰</li>';
    $('#dreams').innerHTML=renderDreams(s.dreams);
    _gv=s.graph_viz||{nodes:[],edges:[]};const _yr=gYears(_gv),_sl=$('#gyslider');if(_yr){_sl.min=_yr[0];_sl.max=_yr[1];if(_sl.dataset.init!=='1'){_sl.value=_yr[1];_sl.dataset.init='1';}}drawGraph();
    $('#graphtop').textContent=((s.graph&&s.graph.length)?('最核心：'+s.graph.join(' · ')):'')+((s.graph_viz&&s.graph_viz.nodes.length)?'　·　点节点筛选时间线 / ▶生长看关系网长出来':'');
    _tl=s.timeline||[]; $('#tlfilters').innerHTML=renderTLfilters(s.timeline_entities); drawTL();
    $('#chronicle').textContent=s.chronicle||'（还没攒下带年份的生平）';
    $('#lastwords').innerHTML=(s.last_words&&s.last_words.length)?li(s.last_words):'<li class=dim>（还没留下嘱托）</li>';
    $('#precepts').innerHTML=(s.precepts&&s.precepts.length)?li(s.precepts):'<li class=dim>（还没立下家训）</li>';
    $('#family').textContent=s.family||'（还没登记家人）';
    $('#familychips').innerHTML=(s.family_members&&s.family_members.length)?s.family_members.map(m=>'<button class=devbtn style="margin:3px" onclick="talkTo(\''+esc(m.name)+'\')">叫 '+esc(m.name)+(m.mem?(' · '+m.mem+'忆'):'')+'</button>').join(''):'';
    $('#care').innerHTML=(s.care&&s.care.length)?li(s.care):'<li class=dim>暂未设置守护对象（见 config/care.yaml）</li>';
    var cp=s.companion||{};
    $('#body').textContent=cp.body?('正「'+cp.body+'」'):'安安静静守着';
    $('#face').textContent=cp.face||'神情平和';
    $('#faceemoji').textContent=cp.face_emoji||'';
    if(cp.face_color){$('#facecard').style.borderLeft='4px solid '+cp.face_color;}
    setFace(s.mood, cp.face_color);              // 那张脸跟着心情活
    $('#reasoning').innerHTML=(cp.reasoning&&cp.reasoning.length)?li(cp.reasoning):'<li class=dim>（还没开口想事）</li>';
    $('#muse').textContent=cp.muse||'';
    $('#meds').innerHTML=(cp.meds&&cp.meds.length)?li(cp.meds):'<li class=dim>这会儿没有要吃的药</li>';
    $('#appts').innerHTML=(cp.appts&&cp.appts.length)?li(cp.appts):'<li class=dim>近期没有就医安排</li>';
    $('#habits').textContent=(cp.habits&&cp.habits.length)?cp.habits.join('　'):'还没立小目标';
    $('#joys').innerHTML=(cp.joys&&cp.joys.length)?li(cp.joys):'<li class=dim>今天的好事还没说给我听</li>';
    $('#mems').innerHTML=li(s.recent_memories);
    $('#jour').innerHTML=li(s.recent_journal);
    if(!inited){$('#speaker').innerHTML=s.people.map(p=>'<option'+(p===s.owner?' selected':'')+'>'+esc(p)+'</option>').join('');inited=true;}
  }catch(e){}
}
function add(who,text,cls){const c=$('#chat');const d=document.createElement('div');d.className='msg '+cls;d.textContent=(who?who+'：':'')+text;c.appendChild(d);c.scrollTop=c.scrollHeight;}
async function ask(t){
  t=(t||'').trim(); if(!t)return;
  const sp=$('#speaker').value; add(sp,t,'me');
  try{
    const r=await (await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,speaker:sp})})).json();
    add(soulName, r.reply, 'soul');
    speak(r.reply);                              // 当场念出来，嘴跟着动
    if(r.associations&&r.associations.length){const c=$('#chat');const d=document.createElement('div');d.className='msg soul';d.style.opacity='0.7';d.style.fontSize='12px';d.textContent='💭 这让我想起：'+r.associations.join('；');c.appendChild(d);c.scrollTop=c.scrollHeight;}
  }catch(e){ add(soulName,'（网络出错）','soul'); }
  refresh();
}
$('#f').addEventListener('submit',e=>{e.preventDefault();const t=$('#msg').value;$('#msg').value='';ask(t);});
$('#brief').addEventListener('click',()=>ask('简报'));
$('#diag').addEventListener('click',()=>ask('系统自检'));
$('#clrtrig').addEventListener('click',()=>ask('清空所有自动化'));
$('#trigf').addEventListener('submit',e=>{e.preventDefault();const t=$('#triginput').value;$('#triginput').value='';ask(t);});
$('#gplay').addEventListener('click',playGraph);
$('#gyslider').addEventListener('input',e=>setGY(e.target.value));
$('#retry').addEventListener('click',async()=>{
  const sp=$('#speaker').value; const b=$('#retry'); b.disabled=true;
  try{
    const r=await (await fetch('/api/retry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({speaker:sp})})).json();
    add(soulName, r.reply||'（已重试）','soul');
  }catch(e){ add(soulName,'（网络出错）','soul'); }
  b.disabled=false; refresh();
});
refresh(); setInterval(refresh,3000);
</script>
</body></html>"""


def start_web(agent, monitor=None, port: int = 8765):
    """在后台线程启动状态页 + 对话接口，返回 server 对象。"""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # 静音访问日志
            pass

        def _send(self, body: bytes, ctype: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/api/status"):
                body = json.dumps(_snapshot(agent, monitor), ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
            else:
                self._send(PAGE.encode("utf-8"), "text/html; charset=utf-8")

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0") or 0)
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                data = {}
            speaker = (data.get("speaker") or _owner(agent)).strip()
            if self.path.startswith("/api/device"):
                res = agent.device_control(speaker, data.get("device"), data.get("action"), data.get("value")) \
                    if hasattr(agent, "device_control") else {"msg": "暂不支持"}
                rows = agent.devices.rows() if getattr(agent, "devices", None) else []
                body = json.dumps({"reply": res.get("msg", ""), "devices": rows}, ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return
            if self.path.startswith("/api/scene"):
                res = agent.run_scene(speaker, data.get("scene")) if hasattr(agent, "run_scene") else {"msg": "暂不支持"}
                rows = agent.devices.rows() if getattr(agent, "devices", None) else []
                body = json.dumps({"reply": res.get("msg", ""), "devices": rows}, ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return
            if self.path.startswith("/api/retry"):
                res = agent.retry_open(speaker) if hasattr(agent, "retry_open") else {"reply": "暂不支持重试"}
                body = json.dumps({"speaker": speaker, "reply": res.get("reply", "")}, ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return
            if self.path.startswith("/api/chat"):
                text = (data.get("text") or "").strip()
                res = agent.handle(speaker, text) if text else {"reply": "", "associations": []}
                body = json.dumps({"speaker": speaker, "reply": res.get("reply", ""),
                                   "associations": res.get("associations", [])},
                                  ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return
            self._send(b"{}", "application/json; charset=utf-8")

    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
