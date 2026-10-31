#!/usr/bin/env bash
# 构建并部署到 Cloudflare Pages。
# 凭证优先用环境变量 CLOUDFLARE_API_TOKEN 与 CLOUDFLARE_ACCOUNT_ID。
# 未设置 token 时，回退到本机 cf CLI 登录态（旧的 macOS 路径）。
set -euo pipefail
cd "$(dirname "$0")"

PROJECT="${PAGES_PROJECT:-math-cheatsheet}"
BRANCH="${PAGES_BRANCH:-main}"
WRANGLER_VERSION="${WRANGLER_VERSION:-4.152.0}"

command -v npx >/dev/null 2>&1 || {
  echo "未找到 npx（需要 Node.js 18+）" >&2
  exit 1
}

if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
    echo "已设置 CLOUDFLARE_API_TOKEN，但缺少 CLOUDFLARE_ACCOUNT_ID。" >&2
    exit 1
  fi
  echo "==> 使用环境变量中的 Cloudflare API Token"
else
  CFG="${CF_CONFIG:-$HOME/Library/Preferences/cloudflare/config/default.json}"
  command -v cf >/dev/null 2>&1 || {
    echo "未设置 CLOUDFLARE_API_TOKEN，也未找到 cf CLI。" >&2
    echo "请导出 CLOUDFLARE_API_TOKEN 和 CLOUDFLARE_ACCOUNT_ID，或先运行 cf auth login。" >&2
    exit 1
  }
  echo "==> 未设置 CLOUDFLARE_API_TOKEN，回退到 cf CLI 登录态（旧路径）"
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
  export CLOUDFLARE_API_TOKEN="$TOKEN"
fi

./build_all.sh

echo "==> 部署到 Cloudflare Pages：$PROJECT（分支 $BRANCH）"
npx --yes "wrangler@${WRANGLER_VERSION}" \
  pages deploy site --project-name "$PROJECT" --branch "$BRANCH"
