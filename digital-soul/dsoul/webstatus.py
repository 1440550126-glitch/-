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
:root{--card:rgba(28,34,50,.72);--line:rgba(255,255,255,.08);--fg:#e9edf5;--mut:#8b97ad;
  --accent:#7fe0c0;--glow:#7fe0c0}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",system-ui,sans-serif;
  margin:0;color:var(--fg);-webkit-font-smoothing:antialiased;
  background:
    radial-gradient(900px 520px at 50% -12%, rgba(127,224,192,.16), transparent 60%),
    radial-gradient(700px 480px at 92% 8%, rgba(255,214,107,.10), transparent 60%),
    linear-gradient(180deg,#0c0f16,#0a0c12);background-attachment:fixed}
.wrap{max-width:680px;margin:0 auto;padding:16px 16px 64px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px;margin:14px 0;
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);box-shadow:0 10px 30px rgba(0,0,0,.26);
  transition:box-shadow .25s}
.card:hover{box-shadow:0 14px 38px rgba(0,0,0,.34)}
.k{color:var(--mut);font-size:12.5px;font-weight:700;letter-spacing:.3px;margin-bottom:9px}
.sub{color:var(--mut);font-size:12.5px;font-weight:700;margin:14px 0 6px}
ul{margin:0;padding-left:18px}li{margin:4px 0;line-height:1.55}
.dim{color:var(--mut)}
.badge{display:inline-block;padding:3px 12px;border-radius:999px;font-size:12px;font-weight:700}
.on{background:rgba(95,221,157,.16);color:#7fe7b4}.off{background:rgba(224,177,95,.16);color:#f0c878}
.row{display:flex;gap:8px;align-items:center;margin:8px 0;flex-wrap:wrap}
select,input,button{font:inherit;font-size:15px;padding:10px 12px;border-radius:12px;border:1px solid var(--line);
  background:rgba(10,12,18,.55);color:var(--fg);outline:none;transition:border .2s}
input:focus,select:focus{border-color:var(--accent)}
input{flex:1;min-width:120px}
button{background:linear-gradient(180deg,#34b88f,#1f8f6c);border:none;color:#06120d;font-weight:800;
  padding:10px 16px;cursor:pointer;box-shadow:0 6px 16px rgba(31,143,108,.28);transition:transform .12s,filter .2s}
button:hover{filter:brightness(1.08)}button:active{transform:translateY(1px)}
.chat{max-height:300px;overflow:auto;display:flex;flex-direction:column;gap:8px;margin:10px 0}
.msg{padding:9px 13px;border-radius:16px;max-width:84%;white-space:pre-wrap;word-break:break-word;line-height:1.5;
  animation:pop .25s ease}
@keyframes pop{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.me{align-self:flex-end;background:linear-gradient(180deg,#3b82f6,#2563eb);color:#fff;border-bottom-right-radius:5px}
.soul{align-self:flex-start;background:rgba(255,255,255,.06);border:1px solid var(--line);border-bottom-left-radius:5px}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:2px 0 4px}
.chip{padding:7px 13px;border-radius:999px;font-size:13.5px;background:rgba(127,224,192,.10);
  border:1px solid rgba(127,224,192,.24);color:#bfeede;cursor:pointer;transition:background .2s,transform .1s;user-select:none}
.chip:hover{background:rgba(127,224,192,.2)}.chip:active{transform:scale(.95)}
.barrow{display:flex;align-items:center;gap:8px;margin:4px 0}.barlab{width:24px;font-size:15px;text-align:center}
.bartrk{flex:1;height:8px;background:rgba(0,0,0,.35);border-radius:6px;overflow:hidden}
.bartrk i{display:block;height:100%;background:linear-gradient(90deg,#1f8f6c,#7fe0c0)}
.devrow{display:flex;align-items:center;gap:8px;margin:6px 0}.devname{width:46px}.devst{flex:1;color:var(--mut);font-size:13px}
.devbtn{padding:6px 13px;font-size:13px;background:rgba(255,255,255,.06);border:1px solid var(--line);color:var(--fg);
  border-radius:10px;cursor:pointer;box-shadow:none;font-weight:600}
.devbtn:hover{filter:brightness(1.18)}
.tlyear{color:var(--accent);font-weight:700;margin:8px 0 2px;border-left:3px solid var(--accent);padding-left:8px}
.tlitem{color:#cbd5e1;font-size:13px;margin:2px 0 2px 16px;position:relative}
.tlitem:before{content:"\2022";color:var(--accent);position:absolute;left:-10px}
.hero{text-align:center;position:relative;overflow:hidden;padding:24px 16px 18px}
.halo{position:absolute;left:50%;top:18px;width:230px;height:230px;transform:translateX(-50%);border-radius:50%;
  background:radial-gradient(circle,var(--glow) 0%,transparent 62%);opacity:.26;filter:blur(8px);
  animation:halo 5s ease-in-out infinite;pointer-events:none}
@keyframes halo{0%,100%{opacity:.18;transform:translateX(-50%) scale(1)}50%{opacity:.34;transform:translateX(-50%) scale(1.08)}}
.avatar{width:144px;height:144px;margin:6px auto;border-radius:50%;position:relative;
  background:radial-gradient(circle at 50% 36%,#33405a,#1a2030);
  box-shadow:0 0 26px 3px var(--glow),inset 0 -10px 26px rgba(0,0,0,.35);
  animation:breathe 4.2s ease-in-out infinite;transition:box-shadow .7s,background .7s}
@keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.045)}}
.avatar.talk{box-shadow:0 0 44px 10px var(--glow),inset 0 -10px 26px rgba(0,0,0,.35)}
.eye{position:absolute;top:55px;width:16px;height:16px;border-radius:50%;background:#f2f6fb;
  animation:blink 5.4s infinite;box-shadow:0 0 8px var(--glow)}
.eye.l{left:44px}.eye.r{right:44px}
@keyframes blink{0%,92%,100%{transform:scaleY(1)}94%,98%{transform:scaleY(.08)}}
.mouth{position:absolute;left:50%;top:94px;width:42px;height:12px;transform:translateX(-50%);
  border-bottom:3px solid #f2f6fb;border-radius:0 0 22px 22px;transition:all .4s}
.mouth.sad{border-bottom:0;border-top:3px solid #f2f6fb;border-radius:22px 22px 0 0;top:100px}
.mouth.flat{height:3px;background:#f2f6fb;border:0;border-radius:3px}
.mouth.talking{animation:talk .26s linear infinite}
@keyframes talk{0%,100%{height:6px}50%{height:20px}}
.heroname{font-size:21px;font-weight:800;margin-top:14px;letter-spacing:.6px}
.heromood{color:var(--mut);font-size:14px;margin-top:4px}
details.card>summary{cursor:pointer;list-style:none;font-weight:700;font-size:14.5px;color:var(--fg);
  display:flex;align-items:center;justify-content:space-between}
details.card>summary::-webkit-details-marker{display:none}
details.card>summary:after{content:"\25be";color:var(--mut);transition:transform .25s}
details.card[open]>summary:after{transform:rotate(180deg)}
details.card[open]>summary{margin-bottom:10px}
</style></head>
<body><div class=wrap>
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
