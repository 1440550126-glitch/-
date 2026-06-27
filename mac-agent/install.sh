#!/bin/bash
# 在 Mac 上一键安装「远程控制 Agent」为开机自启服务（launchd）。
# 用法：
#   REMOTE_SERVER=https://你的服务器 REMOTE_TOKEN=口令 ./install.sh
# 可选：REMOTE_ALLOW_POWER=1（允许远程关机/重启） REMOTE_ALLOW_SHELL=1（允许远程执行命令）
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT="$DIR/agent.mjs"
PLIST_SRC="$DIR/com.jvling.macagent.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.jvling.macagent.plist"
LOG="$HOME/Library/Logs/jvling-macagent.log"

NODE="$(command -v node || true)"
[ -z "$NODE" ] && { echo "✗ 找不到 node，请先安装 Node.js（brew install node）"; exit 1; }
[ -z "${REMOTE_TOKEN:-}" ] && { echo "✗ 请设置 REMOTE_TOKEN（与服务端一致）"; exit 1; }
SERVER="${REMOTE_SERVER:-http://localhost:3000}"
ALLOW_POWER="${REMOTE_ALLOW_POWER:-0}"
ALLOW_SHELL="${REMOTE_ALLOW_SHELL:-0}"

mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s#__NODE__#$NODE#g" \
    -e "s#__AGENT__#$AGENT#g" \
    -e "s#__SERVER__#$SERVER#g" \
    -e "s#__TOKEN__#$REMOTE_TOKEN#g" \
    -e "s#__ALLOW_POWER__#$ALLOW_POWER#g" \
    -e "s#__ALLOW_SHELL__#$ALLOW_SHELL#g" \
    -e "s#__LOG__#$LOG#g" \
    "$PLIST_SRC" > "$PLIST_DST"

launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "✓ 已安装并启动：com.jvling.macagent"
echo "  服务器:   $SERVER"
echo "  关机重启: $([ "$ALLOW_POWER" = "1" ] && echo 开 || echo 关)   执行命令: $([ "$ALLOW_SHELL" = "1" ] && echo 开 || echo 关)"
echo "  日志:     $LOG"
echo "  卸载:     launchctl unload \"$PLIST_DST\" && rm \"$PLIST_DST\""
echo
echo "⚠ 首次运行需在「系统设置 → 隐私与安全性 → 辅助功能/屏幕录制」里授权 node，"
echo "  否则锁屏/输入/截屏会失败。"
