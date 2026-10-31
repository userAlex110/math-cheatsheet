#!/usr/bin/env bash
# 构建并部署到 Cloudflare Pages
set -euo pipefail
cd "$(dirname "$0")"

PROJECT="${PAGES_PROJECT:-math-cheatsheet}"
CFG="${CF_CONFIG:-$HOME/Library/Preferences/cloudflare/config/default.json}"

command -v cf >/dev/null 2>&1 || {
  echo "未找到 cf CLI，请先安装并登录：cf auth login" >&2
  exit 1
}
command -v npx >/dev/null 2>&1 || {
  echo "未找到 npx（需要 Node.js 18+）" >&2
  exit 1
}

# 先让 cf 刷新登录态，再把它保存的 OAuth token 交给 wrangler。
# cf 的 legacy Pages deploy 在 v1 已不支持，实际部署由 wrangler 完成。
cf auth whoami >/dev/null

TOKEN=$(python3 - "$CFG" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1]).expanduser()
try:
    d = json.loads(p.read_text())
    token = d.get("oauth_token", "")
except Exception as e:
    sys.exit(f"读取 cf 登录态失败：{e}")
if not token:
    sys.exit("cf 登录态里没有 oauth_token，请先运行 cf auth login")
print(token)
PY
)

./build_all.sh

echo "==> 部署到 Cloudflare Pages：$PROJECT"
CLOUDFLARE_API_TOKEN="$TOKEN" npx --yes wrangler@4.152.0 \
  pages deploy site --project-name "$PROJECT" --branch main
