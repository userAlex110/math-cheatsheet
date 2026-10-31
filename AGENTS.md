# AGENTS.md

数二背诵小抄：唯一内容源是 `content.py`，同一份内容生成网页（`site/`）和 Word（`数学小抄_数二背诵版.docx`）。
`site/`、`*.docx`、`.mathcache/`、`.preview_tmp/` 都是构建产物，**不要手改，也不要入库**。

## 常用命令（仓库根目录）

| 目的 | 命令 |
| --- | --- |
| 全量构建 + Word 自检 | `./build_all.sh` |
| 只建网页 | `python3 -B web/build.py` |
| 只建 Word | `uv run --no-project --with python-docx python -B build_数学小抄_数二背诵版.py` |
| Word 自检 | `uv run --no-project --with python-docx python -B check_docx.py 数学小抄_数二背诵版.docx` |
| 部署 | `./deploy.sh` |
| 首次装 KaTeX | `cd web && npm install` |

构建成功会打印 `章节 8 · 小节 N · 表格 M · 公式 K`；改完内容要同步 README 里的这三个数。

## 内容规则（违反会构建失败或排版炸）

- `$...$` 里**不能出现中文**（Word 走 pdflatex，直接报错）；中文写在公式外。
- 网页构建用 KaTeX 预渲染，**任何一条公式解析失败就整体失败**，没有降级。
- 表格 `widths` 单位 cm，总和必须 ≤ 18.4（A4 窄边距版心）；列数要和每行单元格数一致。
- `hl=(...)` 是 0 起的行号；单行也要写 `hl=(3,)`，写成 `hl=(3)` 会变成 int。
- 块类型：`S` 章 / `H` 节 / `P` 段 / `N` 旁注 / `T` 表。新增小节用 `1.7b` 这种后缀，避免全篇重编号。
- `**...**`、`!!...!!` 内可嵌 `$...$`，但不能跨行。
- 行内少用 `\dfrac`（Word 行高会被拉高），能写 `0/0` 就用斜杠。

## 构建链路

- 网页：`content.py` → `web/build.py`（分组、KaTeX 预渲染、搜索索引、PWA 版本）→ `site/`。需要 Node 18+ 和 `web/node_modules/katex`。
- Word：`build_数学小抄_数二背诵版.py` → `mathimg.py`（`latex` + `dvipng`，600dpi PNG，按 `sha1(style|latex)` 缓存在 `.mathcache/`）→ `xc_lib.py` 排版 → docx。
- `check_docx.py` 查残留 `**` / `!!` / `$` 标记、表格数与图片数；`build_all.sh` 已包含。
- `.mathcache/` 可整个删掉，只会重渲染，不会丢内容。

## 环境

- macOS / Windows 都需要：Python 3、`uv`、Node 18+、TeX（`latex`、`dvipng`、`newtxmath`）。Windows 用 MiKTeX 或 TeX Live，并确保在 PATH。
- 两个 `.sh` 是 bash 脚本；Windows 用 Git Bash 或 WSL 跑，不要用 cmd / PowerShell 直接执行。
- 部署依赖 `cf` CLI 登录态。`deploy.sh` 默认读 macOS 的 `~/Library/Preferences/cloudflare/config/default.json`；其它平台用 `CF_CONFIG=/path/to/default.json ./deploy.sh`。
- 固定 `npx wrangler@4.152.0`，不要改 latest。Pages 项目 `math-cheatsheet`，分支 `main`。
- 本机预览 Word（仅 macOS）：`/Applications/wpsoffice.app/Contents/MacOS/wpscli word2photo 数学小抄_数二背诵版.docx --output .preview_tmp/wps`。

## Git

- 只提交内容与脚本；`site/`、`*.docx`、缓存、`node_modules/` 已在 `.gitignore`。
- `.gitattributes` 统一 LF：macOS / Windows 都建议 `git config core.autocrlf false`，不要开 `true`。
- 仓库：<https://github.com/userAlex110/math-cheatsheet>

## 验收

1. `./build_all.sh` 全绿，`check_docx.py` 报「残留标记: 0」。
2. 构建打印的节 / 表 / 公式数与 README 一致。
3. 改过公式时，抽查 `site/index.html` 中对应 `data-tex` 是否仍是原 TeX。
