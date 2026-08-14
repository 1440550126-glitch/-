#!/usr/bin/env bash
# recon.sh — 只读侦察：一键盘点攻击面。不修改任何文件，只做 grep/find。
# 用法: bash recon.sh [目标目录，默认当前目录]
# 输出按主题分组，每项给出 文件:行，供漏洞猎手据此逐条深挖。

set -uo pipefail
ROOT="${1:-.}"
cd "$ROOT" 2>/dev/null || { echo "无法进入目录: $ROOT"; exit 1; }

# 优先用 ripgrep，没有则回退 grep -r
if command -v rg >/dev/null 2>&1; then
  SEARCH() { rg -n --no-heading -S \
    -g '!node_modules' -g '!.git' -g '!dist' -g '!build' -g '!*.min.js' \
    -g '!*.lock' -g '!*-lock.json' "$@" . 2>/dev/null; }
  FILES() { rg --files -g '!node_modules' -g '!.git' 2>/dev/null; }
else
  SEARCH() { grep -rnI --exclude-dir=node_modules --exclude-dir=.git \
    --exclude-dir=dist --exclude-dir=build --exclude='*.min.js' \
    -E "${@: -1}" . 2>/dev/null; }
  FILES() { find . -type f -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null; }
fi

hr() { printf '\n═══ %s ═══\n' "$1"; }
sec() { hr "$1"; shift; SEARCH -e "$@" | head -n 60; }

echo "############################################################"
echo "#  漏洞猎手侦察报告  target: $(pwd)"
echo "#  以下每一项都是「去哪看」的线索，需读全上下文再定性。"
echo "############################################################"

hr "技术栈 / 依赖 / 配置文件"
FILES | grep -iE '(package\.json|requirements\.txt|go\.mod|pom\.xml|Gemfile|composer\.json|Cargo\.toml|Dockerfile|docker-compose|\.env|\.env\.example|nginx|\.github/workflows|wrangler|vercel|serverless)' | head -n 40

hr "疑似硬编码密钥 / 口令 / token（重点核实真伪与是否上线）"
SEARCH -e "(?i)(password|passwd|secret|api[_-]?key|apikey|access[_-]?key|private[_-]?key|token|mchkey|appsecret|client[_-]?secret)\s*[:=]\s*['\"][^'\"]{6,}" | grep -viE '(example|placeholder|your[_-]|xxx|<|process\.env|os\.environ|getenv)' | head -n 50

hr "私钥块 / 常见密钥格式"
SEARCH -e "(BEGIN (RSA|EC|OPENSSH|PGP|PRIVATE) KEY|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-)" | head -n 20

hr "路由 / 接口定义（攻击入口）"
SEARCH -e "(app|router|route|server)\.(get|post|put|patch|delete|all)\s*\(|@(Get|Post|Put|Delete|RequestMapping|RestController)|addRoute|routes\s*[:=]|createServer|req\.url\s*===" | head -n 80

hr "鉴权 / 会话 / 权限判定点（核实每个入口是否都过了鉴权）"
SEARCH -e "(?i)(requireAuth|requireAdmin|isAdmin|authGuard|authenticate|authorize|verifyToken|jwt\.(verify|decode|sign)|checkPermission|hasRole|req\.(user|session)|ctx\.(user|state)|middleware)" | head -n 60

hr "SQL / DB 查询（找拼接=注入）"
SEARCH -e "(?i)(SELECT|INSERT|UPDATE|DELETE)\s+.*(\+|\\\$\{|\`)|\.(query|execute|exec|prepare|raw)\s*\(|db\.(get|all|run|prepare)|sequelize\.query|knex\.raw|\\\$where|\\\$regex" | head -n 60

hr "命令执行 / 代码求值（RCE 面）"
SEARCH -e "(?i)(child_process|exec\s*\(|execSync|spawn\s*\(|execFile|\beval\s*\(|new Function|vm\.(run|compile)|os\.(system|popen)|subprocess\.|Runtime\.getRuntime|deserialize|pickle\.loads)" | head -n 40

hr "文件系统操作 + 可能的路径穿越"
SEARCH -e "(?i)(readFile|writeFile|createReadStream|createWriteStream|unlink|sendFile|fs\.(open|read|write)|path\.join|res\.download|extract|unzip|open\s*\()" | grep -iE "(req|param|query|body|input|user|name|path|file)" | head -n 40

hr "外发 HTTP 请求（SSRF 面）"
SEARCH -e "(?i)(fetch\s*\(|axios|http\.(get|request)|https\.(get|request)|request\s*\(|urllib|requests\.(get|post)|new URL\s*\(|got\s*\(|superagent)" | head -n 40

hr "HTML 渲染 / DOM sink（XSS 面）"
SEARCH -e "(?i)(innerHTML|outerHTML|insertAdjacentHTML|document\.write|dangerouslySetInnerHTML|v-html|\{\{\{|res\.send\s*\(|res\.write\s*\(.*req)" | head -n 40

hr "对象合并 / 批量赋值（原型链污染 + Mass Assignment）"
SEARCH -e "(?i)(Object\.assign\s*\([^,]*,\s*req|\{\s*\.\.\.req\.(body|query)|merge\s*\(|deepMerge|extend\s*\(|_\.merge|_\.set|new \w+\(req\.body\)|\.update\s*\(req\.body)" | head -n 30

hr "弱随机 / 弱加密 / 危险比较"
SEARCH -e "(?i)(Math\.random|md5|sha1[^0-9]|createHash\(['\"](md5|sha1)|ECB|===\s*(token|sig|signature|hmac)|==\s*(token|sig|signature))" | head -n 30

hr "CORS / 安全响应头"
SEARCH -e "(?i)(Access-Control-Allow-Origin|Access-Control-Allow-Credentials|Content-Security-Policy|X-Frame-Options|Set-Cookie|HttpOnly|SameSite|cors\s*\()" | head -n 30

hr "调试 / 危险开关 / TODO-FIXME-XXX-HACK（常藏坑）"
SEARCH -e "(?i)(NODE_ENV|debug\s*[:=]\s*true|DEBUG=|console\.log\(.*(password|token|secret)|TODO|FIXME|XXX|HACK|临时|后门|绕过|hardcode|hard-code|写死)" | head -n 40

hr "上传 / multipart / 文件类型处理"
SEARCH -e "(?i)(multipart|formidable|multer|busboy|upload|Content-Type|mimetype|originalname|filename)" | head -n 30

echo
echo "############################################################"
echo "# 侦察完成。下一步：按 SKILL.md 阶段 1 从「入口→汇聚点」逐条 taint 追踪，"
echo "# 每个候选走全链路验证后，用 report-template.md 出报告。"
echo "############################################################"
