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
- 生产部署走 GitHub Actions（`.github/workflows/pages.yml`）。推送到 `main`，或在 `main` 上手动运行：`./build_all.sh` 之后执行 `npx wrangler@4.152.0 pages deploy site --project-name math-cheatsheet --branch main`。凭证是仓库 Secrets `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`。地址仍是 <https://math-cheatsheet.pages.dev>。Pull Request 只构建和自检。
- 本机 `./deploy.sh` 会先构建再部署。已设置 `CLOUDFLARE_API_TOKEN` 和 `CLOUDFLARE_ACCOUNT_ID` 就用这两项；没设 token 时才回退到 `cf` CLI 登录态（旧路径，macOS 默认读 `~/Library/Preferences/cloudflare/config/default.json`，其它路径用 `CF_CONFIG`）。
- 固定 `npx wrangler@4.152.0`，不要改 latest。Pages 项目 `math-cheatsheet`，生产分支 `main`。
- 本机预览 Word（仅 macOS）：`/Applications/wpsoffice.app/Contents/MacOS/wpscli word2photo 数学小抄_数二背诵版.docx --output .preview_tmp/wps`。

## Git

- 只提交内容与脚本；`site/`、`*.docx`、缓存、`node_modules/` 已在 `.gitignore`。`inbox/` 里的原始笔记要入库。
- `.gitattributes` 统一 LF：macOS / Windows 都建议 `git config core.autocrlf false`，不要开 `true`。
- 仓库：<https://github.com/userAlex110/math-cheatsheet>
- 内容改动走 PR，不要直接推 `main`。合并到 `main` 会触发生产部署。

## 笔记入库

原始笔记放 `inbox/`（markdown、摘录、图片）。构建不读这个目录。推导、题号、分数、心态不进小抄。一次笔记一个 PR，按下面五步做完。

1. **分类**。先判断是公式、判定、触发词，还是易错。公式和判定放进对应章里已有的小节；触发词进 §7；易错进 §8。没有合适小节时用 `1.7b` 这种后缀新开一节，不要全篇重编号。
2. **去重**。在 `content.py` 里搜同一条结论；比对公式时把空格、以及 `\frac` 和 `\dfrac` 的差别算进去。已经有、而且没错：不改 `content.py`，PR 里写明重复，并删掉 `inbox/` 里的原文。已经有、但说错了或少了易错：就地改正。完全没有：再新增。
3. **标注**。只在这次动过的 `B(...)` 上一行加注释，日期用当天，格式 `YYYY-MM-DD`。注释不会进网页和 Word，不要把标记写进正文。
   - 新结论：`# 新增 2026-10-31`
   - 纠正已有表述，或补一条易错：`# 错题 2026-10-31`
   一条改动只标一种。旧注释留着，不要改历史标记。`$...$` 里不能写这些中文。
4. **构建**。仓库根目录跑 `./build_all.sh`。节 / 表 / 公式数变了就改 README 里的三个数。`check_docx.py` 必须是「残留标记: 0」。
5. **开 PR**。用中文写清：来自哪份笔记、分类结果、去重时丢掉了什么、标了哪些新增或错题。不要直接推 `main`，也不要合并。合并到 `main` 会按 `.github/workflows/pages.yml` 部署到 <https://math-cheatsheet.pages.dev>。消化完的原文从 `inbox/` 删掉，随这个 PR 一起提交。

## 验收

1. `./build_all.sh` 全绿，`check_docx.py` 报「残留标记: 0」。
2. 构建打印的节 / 表 / 公式数与 README 一致。
3. 改过公式时，抽查 `site/index.html` 中对应 `data-tex` 是否仍是原 TeX。
