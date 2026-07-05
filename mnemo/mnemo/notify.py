"""通知推送：让 7×24 的提醒/任务结果真正触达用户，而不仅躺在日志里。

渠道（按 config.notify.channel 与可用性自动选择）：
- desktop：macOS osascript / Linux notify-send / 终端响铃兜底
- webhook：POST JSON 到 config.notify.webhook（Slack/Discord/Mattermost/自建均可）
- 始终回退到 stdout，绝不静默失败

配置：
  notify.channel    auto | desktop | webhook | none   （默认 auto）
  notify.webhook    URL
  notify.on_reminder  到点提醒是否推送（默认 true）
  notify.on_task      守护任务完成是否推送（默认 false，避免刷屏）
纯标准库，零第三方依赖。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request


def desktop(title: str, message: str) -> bool:
    """尝试系统桌面通知，成功返回 True。"""
    if shutil.which("osascript"):                     # macOS
        scpt = f'display notification {json.dumps(message)} with title {json.dumps(title)}'
        try:
            subprocess.run(["osascript", "-e", scpt], capture_output=True, timeout=10)
            return True
        except Exception:  # noqa: BLE001
            return False
    if shutil.which("notify-send"):                   # Linux 桌面
        try:
            subprocess.run(["notify-send", title, message], capture_output=True, timeout=10)
            return True
        except Exception:  # noqa: BLE001
            return False
    return False


def email(cfg: dict, title: str, message: str) -> bool:
    """通过 SMTP 发邮件（stdlib smtplib）。cfg: {smtp_host,port,user,password,to,from,starttls}。"""
    import smtplib
    from email.message import EmailMessage
    host, to = cfg.get("smtp_host"), cfg.get("to")
    if not host or not to:
        return False
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = cfg.get("from") or cfg.get("user") or "mnemo@localhost"
    msg["To"] = to
    msg.set_content(message)
    try:
        with smtplib.SMTP(host, int(cfg.get("port", 587)), timeout=15) as s:
            if cfg.get("starttls", True):
                s.starttls()
            if cfg.get("user"):
                s.login(cfg["user"], cfg.get("password", ""))
            s.send_message(msg)
        return True
    except Exception:  # noqa: BLE001
        return False


def webhook(url: str, title: str, message: str, timeout: int = 10) -> bool:
    """POST 通用 JSON；同时带 text/content/title 字段以兼容主流 IM webhook。"""
    text = f"{title}: {message}" if title else message
    payload = json.dumps({"text": text, "content": text, "title": title,
                          "message": message}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:  # noqa: BLE001
        return False


def notify(config, message: str, title: str = "Mnemo") -> str:
    """按配置推送，返回实际使用的渠道名（desktop/webhook/stdout/none）。"""
    channel = (config.get("notify.channel", "auto") if config else "auto") or "auto"
    if channel == "none":
        return "none"
    hook = config.get("notify.webhook") if config else None
    email_cfg = (config.get("notify.email") if config else None) or {}

    if channel in ("auto", "webhook") and hook and webhook(hook, title, message):
        return "webhook"
    if channel in ("auto", "email") and email_cfg.get("smtp_host") and email(email_cfg, title, message):
        return "email"
    if channel in ("auto", "desktop") and desktop(title, message):
        return "desktop"
    print(f"🔔 {title}：{message}")                    # 始终兜底
    return "stdout"
