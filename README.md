# 数学小抄（数二背诵版）

把考研数学二整理成**直接可背**的小抄：只留公式、判定结论、触发词；推导、题号、出处一律不放。

同一份 `content.py` 生成两个成品：**网页版**（可搜索、可自测、可离线）和 **Word 打印版**。

## 成品

- **网页版**：<https://math-cheatsheet.pages.dev>
  8 章 · 60 节 · 69 张表 · 1467 条公式；支持搜索、章节跳转、背诵进度、自测遮公式、PWA 离线。
- `数学小抄_数二背诵版.docx` —— 69 张表，1467 个公式（每式一张 600dpi 图）。
  §1 极限 → §2 一元微分 → §3 积分 → §4 多元 → §5 微分方程 → §6 线代 → §7 触发词秒杀 → §8 易错红榜。

网页公式在构建时用 KaTeX 预渲染成 HTML，浏览器端不跑公式 JS：矢量、可选中、无闪烁；KaTeX 字体自托管，不依赖 CDN。

## 素材来源

- `~/Documents/myNote/codeRoom/daily 日记/2026/2026-10/2026-10-19.md`（2014 数二真题全卷复盘）
- `…/2026-10-20.md`（当天 7 道大题的卡点复盘）
- `…/2026-10-22.md`（17 / 19 / 20 / 21 题复盘：一阶线性、法线截距、双纽线、侧面积）
- `…/2026-10-23.md` 及手写图 `assets/1792725947404.jpg`、`assets/1792725947445.jpg`（三阶常系数齐次、`(A|E)→(PA|P)`、双纽线、三角换元、黎曼和、全微分）
- `…/Inbox/考研/数学/复习手册-高数.md`、`复习手册-线代.md`（全面版，作为准确性来源）
- `导出对话/*.json`（2016 / 2017 真题复盘、冲刺复盘的 Gemini 对话；只提炼「不会 / 模糊 / 高频」的点，不复述题目）
- 黄色便签 `assets/1792500501546.jpg` 的原话：**「数学：要背要记知识点整理出来」**

手册是「资料」，小抄是「要背」——不要把手册整段搬进来。真题对话只取结论与易错，题号、分数、心态一律不进小抄。

## 文件

| 文件 | 作用 |
| --- | --- |
| `content.py` | 唯一内容源：DOC 元信息 + BLOCKS（`S/H/P/N/T` 五种块） |
| `mathimg.py` | `$latex$` → 600dpi PNG（`latex` + `dvipng`，newtxmath） |
| `xc_lib.py` | python-docx 排版库（A4 窄边距、列宽双写、相邻表留隙） |
| `build_数学小抄_数二背诵版.py` | 扫公式 → 渲染 → 排版 → 出 docx |
| `check_docx.py` | Word 交付自检：残留标记、表格/图片计数 |
| `web/build.py` | `content.py` → `site/`：分组、KaTeX 预渲染、搜索索引、资源版本 |
| `web/render_math.mjs` | 批量调用 KaTeX，任何公式解析失败即构建失败 |
| `web/static/style.css` | 网页视觉：作业本纸面、红笔批注、深色主题、打印样式 |
| `web/static/app.js` | 主题、进度、自测、章节高亮、搜索、PWA 注册 |
| `web/static/sw.js` | 离线缓存（导航 network-first，静态资源 cache-first） |
| `build_all.sh` | 一键全量：Word 构建 + 自检 + 网页构建 |
| `deploy.sh` | 本机全量构建后部署；优先读 Cloudflare 环境变量，否则回退到 `cf` 登录态 |
| `.github/workflows/pages.yml` | GitHub Actions：PR 只构建自检；推送到 `main` 或在 `main` 上手动运行则部署 |
| `inbox/` | 还没写进小抄的原始笔记；构建不读取。处理步骤见 `AGENTS.md` |
| `导出对话/` | 真题复盘对话的原始导出（Gemini JSON），新增条目的来源；构建不读取 |

`site/` 是构建产物，不要手改；每次构建会整体重建。

## 版本管理

- 仓库：<https://github.com/userAlex110/math-cheatsheet>（公开）。
- 只入库**内容与构建脚本**：`content.py`、构建脚本、网页静态资源、`导出对话/`、`inbox/`。`site/`、`*.docx`、`.mathcache/`、`.preview_tmp/`、`node_modules/` 都在 `.gitignore` 里，随时能重建，不进历史。
- 日常流程：笔记先放 `inbox/` → 改 `content.py` → `./build_all.sh` 自检 → 开 Pull Request（CI 只构建和自检）→ 合并到 `main`。合并会触发生产部署，地址仍是 <https://math-cheatsheet.pages.dev>。

## 重新生成

### 网页版

```bash
cd "/Users/mac/Documents/Default Project/数学小抄"
python3 -B web/build.py
```

首次构建前需要 KaTeX：

```bash
cd web && npm install
```

### Word 版

```bash
uv run --no-project --with python-docx python -B build_数学小抄_数二背诵版.py
uv run --no-project --with python-docx python -B check_docx.py 数学小抄_数二背诵版.docx
```

### 一键全量

```bash
./build_all.sh
```

改内容只改 `content.py`，不手改 docx，也不手改 `site/`。公式缓存 `.mathcache/` 可随时删除（会重渲染）。

## 部署

生产环境由 GitHub Actions 直接上传到 Cloudflare Pages，项目 `math-cheatsheet`，地址仍是 <https://math-cheatsheet.pages.dev>。

| 事件 | 做什么 |
| --- | --- |
| Pull Request | `./build_all.sh`（Word 构建、自检、网页构建），不部署 |
| 推送到 `main` | 同上，然后部署到生产 |
| 在 `main` 上手动运行「构建与部署」 | 与推送到 `main` 相同 |

部署命令固定为：

```bash
npx wrangler@4.152.0 pages deploy site --project-name math-cheatsheet --branch main
```

`--branch main` 对应 Pages 的生产分支，所以更新的是 `math-cheatsheet.pages.dev`，不会另开一个预览地址。凭证用仓库已有的 Secrets：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`。不要改 wrangler 的版本号。

**合并到 `main` 会立刻更新线上小抄。** 内容改动先开 PR，看 CI 通过再合并。

本机仍可一键构建并部署：

```bash
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=...
./deploy.sh
```

`./deploy.sh` 先跑 `./build_all.sh`，再用上面同一条 wrangler 命令。已经设置这两个环境变量时直接用它们（不限 macOS）。没设 `CLOUDFLARE_API_TOKEN` 时，才回退到本机 `cf` CLI 登录态：默认读 macOS 的 `~/Library/Preferences/cloudflare/config/default.json`，其它路径用 `CF_CONFIG=/path/to/default.json ./deploy.sh`。这是旧路径。`cf` v1 的 `cf pages deploy` 不支持 legacy Pages，实际仍由 wrangler 上传。

- 默认项目名 `math-cheatsheet`，分支 `main`。要换项目：`PAGES_PROJECT=其他名字 ./deploy.sh`；要换分支：`PAGES_BRANCH=其他分支 ./deploy.sh`。
- 换全新项目时先建一次：`npx wrangler@4.152.0 pages project create 名字 --production-branch main --force`。
- 账号没有自定义域名配额，使用 `*.pages.dev`。
- 网页首次打开后由 Service Worker 缓存；断网或弱网仍可背诵。版本号变化会自动清旧缓存。

## 为什么要用图片而不是 Word 公式

本机没装 Cambria Math，pandoc 生成的 OMML 公式在 WPS 里 **全部显示成方框**（实测），
LibreOffice 也会丢中文。TeX 渲染成 600dpi PNG 后，WPS / LibreOffice / 打印四处一致。

网页版不受这个限制：KaTeX 直接输出 HTML + 字体，公式可选中、可缩放。

## 已知坑

- `$…$` 里不能出现中文（pdflatex 报 Unicode character not set up）。中文写公式外，或用 `n=2k / n=2k+1` 的纯数学写法。
- `**…**` / `!!…!!` 内可再嵌 `$…$`（`add_runs` 递归），但别跨行嵌套。
- 行内 `\dfrac` 会拉高行：能写 `0/0`、`∞/∞` 的用斜杠式。
- 表格列宽总和 ≤ 18.4 cm；图片宽度由 `img_max` 自动截断。
- 网页构建依赖 `web/node_modules/katex`；`site/` 被清空重建，不要往里放手工文件。
- 预览 Word 用 WPS：`/Applications/wpsoffice.app/Contents/MacOS/wpscli word2photo 文件.docx --output .preview_tmp/wps`（LibreOffice 缺中文字体，不能作判据）。
