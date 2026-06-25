#!/usr/bin/env bash
# 更新部署：拉新代码 → 语法检查 → 重启 → 健康检查。在服务器项目根目录执行。
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"

echo "→ 拉取最新代码";  git pull --ff-only
echo "→ 语法自检";      npm run check
echo "→ 重启服务";      sudo systemctl restart jvling
sleep 2
echo -n "→ 健康检查: "
if curl -fsS http://localhost:3000/api/health >/dev/null; then
  echo "✅ OK"
else
  echo "❌ 失败，排查： journalctl -u jvling -n 50 --no-pager"; exit 1
fi
