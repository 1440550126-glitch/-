"""推断：把零散的迹象连起来想——血压偏高又总头晕、睡不好难怪没精神、药没按时吃血压才上来。
不是单看一条，是几条凑一块儿推个结论。给的是关切的提醒，不是诊断。纯逻辑、可单测。

signals 由 Agent 从 understanding(常烦心的事) / vitals(体征异常) / medication(漏没漏药) 等汇集。
"""

from __future__ import annotations


def infer(signals) -> list:
    """从一组迹象里推出几条关切的结论（可能为空）。"""
    s = signals or {}
    concerns = set(s.get("concerns", []) or [])
    symptoms = str(s.get("symptoms", "") or "")
    out = []

    if "睡不好" in concerns and "太累" in concerns:
        out.append("你这阵子又睡不好又喊累——八成是没睡踏实拖累了精神。先把觉睡好，别的才有劲。")
    if "睡不好" in concerns and s.get("worried"):
        out.append("睡不着，常是心里压着事。把愁的跟我念叨念叨，兴许就睡得着了。")
    if s.get("bp_high") and ("头晕" in symptoms or "头疼" in symptoms):
        out.append("血压最近偏高，又总头晕——这俩怕是有关联，别扛着，抽空去查查，我陪你。")
    if s.get("bp_high") and s.get("med_missed"):
        out.append("血压偏高，偏巧又有几顿药没按时吃——多半有关系，药可千万别落下。")
    if "手头紧" in concerns and "工作烦" in concerns:
        out.append("钱紧又为工作烦心，这两样常缠一块儿——别急，一件一件来，咱合计合计。")
    if "太累" in concerns and "身体" in concerns:
        out.append("总喊累、身子又不舒坦——别硬撑，身体是本钱，该歇就歇、该查就查。")
    if "孤单" in concerns and s.get("long_unseen"):
        out.append("你这阵子有点孤单，家里人也少露面——要不我帮你张罗，给谁打个电话聚聚？")
    return out
