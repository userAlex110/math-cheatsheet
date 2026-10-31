#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""content.py → site/ 纯静态网页。

- 公式在构建时用 KaTeX 预渲染成 HTML（浏览器端零公式 JS）
- 输出单页 index.html + 搜索索引 + 自托管 KaTeX 字体
- 任何公式解析失败都会让构建失败
"""
from __future__ import annotations

import gzip
import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = ROOT / "site"
STATIC = HERE / "static"
DOCX = ROOT / "数学小抄_数二背诵版.docx"
KATEX_DIST = HERE / "node_modules" / "katex" / "dist"

MATH_RE = re.compile(r"\$([^$]+)\$")
CH_RE = re.compile(r"^§\s*(\d+)[　\s]+(.+)$")
H_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)*[a-z]?)[　\s]+(.+)$")

SHORT = {
    "1": "极限",
    "2": "微分",
    "3": "积分",
    "4": "多元",
    "5": "方程",
    "6": "线代",
    "7": "秒杀",
    "8": "易错",
}

ICONS = {
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16.6 16.6 4 4"/></svg>',
    "moon": '<svg class="i-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.6A8.2 8.2 0 0 1 9.4 4 8.2 8.2 0 1 0 20 14.6Z"/></svg>',
    "sun": '<svg class="i-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2.6v2M12 19.4v2M2.6 12h2M19.4 12h2M5.4 5.4l1.4 1.4M17.2 17.2l1.4 1.4M18.6 5.4l-1.4 1.4M6.8 17.2l-1.4 1.4"/></svg>',
    "hide": '<svg class="i-hide" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3l18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.5 5.4A9.9 9.9 0 0 1 12 5c5.2 0 9 4.4 9 7 0 .9-.6 2.1-1.6 3.2"/><path d="M6.3 6.4C4.2 7.8 3 9.6 3 12c0 2.6 3.8 7 9 7 1.2 0 2.3-.2 3.3-.7"/></svg>',
    "show": '<svg class="i-show" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" aria-hidden="true"><path d="M3 12c0-2.6 3.8-7 9-7s9 4.4 9 7-3.8 7-9 7-9-4.4-9-7Z"/><circle cx="12" cy="12" r="2.4"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
}


def load_content():
    spec = importlib.util.spec_from_file_location("content", ROOT / "content.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def esc(s: str) -> str:
    return html.escape(s, quote=False)


# ---------------------------------------------------------------- 结构化
def group_blocks(blocks):
    chapters = []
    cur_ch = None
    cur_topic = None
    used_ids = set()

    def close_topic():
        nonlocal cur_topic
        cur_topic = None

    def close_chapter():
        nonlocal cur_ch
        close_topic()
        cur_ch = None

    for kind, payload in blocks:
        if kind == "S":
            close_chapter()
            m = CH_RE.match(str(payload))
            num, title = (m.group(1), m.group(2)) if m else ("?", str(payload))
            cur_ch = {
                "num": num,
                "title": title,
                "id": f"ch-{num}",
                "preface": [],
                "preface_text": [],
                "preface_tex": [],
                "topics": [],
            }
            chapters.append(cur_ch)
        elif kind == "H":
            assert cur_ch is not None, "H 出现在任何 S 之前"
            close_topic()
            m = H_RE.match(str(payload))
            num, title = (m.group(1), m.group(2)) if m else (str(len(cur_ch["topics"]) + 1), str(payload))
            tid = "s-" + num.replace(".", "-")
            if tid in used_ids:
                tid += "-2"
            used_ids.add(tid)
            cur_topic = {
                "num": num,
                "title": title,
                "id": tid,
                "blocks": [],
                "text": [title],
                "tex": [],
            }
            cur_ch["topics"].append(cur_topic)
        else:
            assert cur_ch is not None, "内容块出现在任何 S 之前"
            bucket = cur_topic["blocks"] if cur_topic else cur_ch["preface"]
            bucket.append((kind, payload))
            if cur_topic:
                target = cur_topic
            else:
                target = {"text": cur_ch["preface_text"], "tex": cur_ch["preface_tex"]}
            if kind == "T":
                p = payload
                cells = [str(h) for h in p.get("head") or []] + [
                    str(c) for row in p["rows"] for c in row
                ]
                target["text"].extend(MATH_RE.sub(" ", s) for s in cells)
                target["tex"].extend(
                    m.group(1) for s in cells for m in MATH_RE.finditer(s)
                )
            else:
                text = str(payload)
                target["text"].append(MATH_RE.sub(" ", text))
                target["tex"].extend(m.group(1) for m in MATH_RE.finditer(text))
    close_chapter()
    return chapters


def iter_texts(chapters):
    for ch in chapters:
        for kind, payload in ch["preface"]:
            yield kind, payload
        for t in ch["topics"]:
            yield "H", t["title"]
            for kind, payload in t["blocks"]:
                yield kind, payload


def collect_math(chapters):
    block_set, inline_set = set(), set()
    for kind, payload in iter_texts(chapters):
        if kind == "T":
            p = payload
            for s in [str(h) for h in p.get("head") or []] + [
                str(c) for row in p["rows"] for c in row
            ]:
                block_set.update(m.group(1).strip() for m in MATH_RE.finditer(s))
        else:
            inline_set.update(m.group(1).strip() for m in MATH_RE.finditer(str(payload)))
    return block_set, inline_set


def render_math(block_set, inline_set):
    items = [
        {"key": "b:" + tex, "tex": tex, "block": True} for tex in sorted(block_set)
    ] + [
        {"key": "i:" + tex, "tex": tex, "block": False} for tex in sorted(inline_set)
    ]
    proc = subprocess.run(
        ["node", str(HERE / "render_math.mjs")],
        input=json.dumps(items, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=HERE,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or "KaTeX 渲染失败\n")
        sys.exit(1)
    return json.loads(proc.stdout), len(items)


def make_inline(rendered):
    def inline(text: str, style: str = "inline") -> str:
        pieces = []

        def keep(m):
            tex = m.group(1).strip()
            key = ("b:" if style == "block" else "i:") + tex
            pieces.append(tex)
            return f"\x00{len(pieces) - 1}\x00"

        tmp = MATH_RE.sub(keep, str(text))
        tmp = esc(tmp)
        tmp = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", tmp, flags=re.S)
        tmp = re.sub(r"!!(.+?)!!", r'<em class="warn">\1</em>', tmp, flags=re.S)
        tmp = re.sub(r"　{2,}", lambda m: "<wbr>" + m.group(0), tmp)

        def restore(m):
            i = int(m.group(1))
            tex = pieces[i]
            key = ("b:" if style == "block" else "i:") + tex
            return (
                f'<span class="math" data-tex="{html.escape(tex, quote=True)}">'
                f"{rendered[key]}</span>"
            )

        return re.sub(r"\x00(\d+)\x00", restore, tmp)

    return inline


def table_html(p, inline) -> str:
    widths = p["widths"]
    total = sum(widths)
    ncols = len(widths)
    cols = "".join(f'<col style="width:{w / total * 100:.3f}%">' for w in widths)
    head = p.get("head") or []
    thead = ""
    if any(str(h).strip() for h in head):
        thead = "<thead><tr>" + "".join(
            f"<th>{inline(h, 'block')}</th>" for h in head
        ) + "</tr></thead>"
    hl = set(p.get("hl") or ())
    rows = []
    for i, row in enumerate(p["rows"]):
        cls = ' class="hl"' if i in hl else ""
        rows.append(
            f"<tr{cls}>"
            + "".join(f"<td>{inline(c, 'block')}</td>" for c in row)
            + "</tr>"
        )
    return (
        '<div class="table-wrap">'
        f'<table class="cols-{ncols}">{("<colgroup>" + cols + "</colgroup>") if cols else ""}'
        f"{thead}<tbody>{''.join(rows)}</tbody></table>"
        "</div>"
    )


def block_html(kind, payload, inline) -> str:
    if kind == "T":
        return table_html(payload, inline)
    if kind == "P":
        return f'<p class="para">{inline(payload)}</p>'
    if kind == "N":
        return f'<aside class="note">{inline(payload)}</aside>'
    raise ValueError(kind)


def build_body(chapters, inline):
    out = []
    for ch in chapters:
        parts = [
            f'<section class="chapter" id="{ch["id"]}">',
            '<header class="ch-head">',
            f'<h2><span class="ch-num">§{ch["num"]}</span>{inline(ch["title"])}</h2>',
            "</header>",
        ]
        if ch["preface"]:
            parts.append('<div class="ch-preface">')
            parts.extend(block_html(k, p, inline) for k, p in ch["preface"])
            parts.append("</div>")
        for t in ch["topics"]:
            parts.append(f'<section class="topic" id="{t["id"]}">')
            parts.append(
                '<h3 class="t-head">'
                f'<a class="t-num" href="#{t["id"]}" aria-label="链接到 {t["num"]}">{t["num"]}</a>'
                f'<span class="t-title">{inline(t["title"])}</span>'
                f'<button class="mark" type="button" data-id="{t["id"]}" aria-pressed="false" '
                f'aria-label="标记 {t["num"]} 已背"><span></span></button>'
                "</h3>"
            )
            parts.extend(block_html(k, p, inline) for k, p in t["blocks"])
            parts.append("</section>")
        parts.append("</section>")
        out.append("\n".join(parts))
    return "\n".join(out)


def check_markers(chapters):
    for kind, payload in iter_texts(chapters):
        if kind == "T":
            cells = [str(h) for h in payload.get("head") or []] + [
                str(c) for row in payload["rows"] for c in row
            ]
        else:
            cells = [str(payload)]
        for cell in cells:
            plain = MATH_RE.sub("", cell)
            for marker in ("**", "!!"):
                if plain.count(marker) % 2:
                    sys.exit(f"未闭合的标记 {marker}：{cell[:90]}")


def build_search(chapters, inline):
    index = []
    for ch in chapters:
        chtitle = f'§{ch["num"]} {ch["title"]}'
        if ch["preface"]:
            text = re.sub(r"\s+", " ", " ".join(ch["preface_text"])).strip()
            text = text.replace("**", "").replace("!!", "")
            index.append(
                {
                    "id": ch["id"],
                    "ch": chtitle,
                    "num": "",
                    "title": ch["title"],
                    "titleHtml": inline(ch["title"]),
                    "text": text,
                    "tex": " ".join(ch["preface_tex"]),
                }
            )
        for t in ch["topics"]:
            text = " ".join(t["text"])
            text = re.sub(r"\s+", " ", text).strip()
            text = text.replace("**", "").replace("!!", "")
            index.append(
                {
                    "id": t["id"],
                    "ch": chtitle,
                    "num": t["num"],
                    "title": t["title"],
                    "titleHtml": inline(t["title"]),
                    "text": text,
                    "tex": " ".join(t["tex"]),
                }
            )
    return index


def counts(chapters):
    tables = formulas = topics = 0
    for ch in chapters:
        for kind, payload in ch["preface"]:
            if kind == "T":
                tables += 1
                formulas += sum(
                    len(MATH_RE.findall(str(s)))
                    for s in [str(h) for h in payload.get("head") or []]
                    + [str(c) for row in payload["rows"] for c in row]
                )
            else:
                formulas += len(MATH_RE.findall(str(payload)))
        for t in ch["topics"]:
            topics += 1
            formulas += len(MATH_RE.findall(t["title"]))
            for kind, payload in t["blocks"]:
                if kind == "T":
                    tables += 1
                    formulas += sum(
                        len(MATH_RE.findall(str(s)))
                        for s in [str(h) for h in payload.get("head") or []]
                        + [str(c) for row in payload["rows"] for c in row]
                    )
                else:
                    formulas += len(MATH_RE.findall(str(payload)))
    return len(chapters), topics, tables, formulas


def human_size(n: int) -> str:
    return f"{n / 1048576:.2f} MB" if n >= 1048576 else f"{n / 1024:.0f} KB"


def main() -> None:
    started = time.time()
    if not KATEX_DIST.exists():
        sys.exit("缺少 KaTeX：先在 web/ 里运行 npm install")

    mod = load_content()
    chapters = group_blocks(mod.BLOCKS)
    check_markers(chapters)
    block_set, inline_set = collect_math(chapters)
    rendered, rendered_count = render_math(block_set, inline_set)
    inline = make_inline(rendered)
    body = build_body(chapters, inline)
    index = build_search(chapters, inline)
    n_ch, n_topics, n_tables, n_formulas = counts(chapters)

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "assets").mkdir(parents=True)

    for name in ("style.css", "app.js", "icon.svg", "icon-180.png", "icon-192.png", "icon-512.png"):
        src = STATIC / name
        if not src.exists():
            sys.exit(f"缺少静态文件：{src}")
        shutil.copy2(src, SITE / "assets" / name)
    (SITE / "assets" / "katex").mkdir(exist_ok=True)
    (SITE / "assets" / "katex" / "fonts").mkdir(exist_ok=True)
    shutil.copy2(KATEX_DIST / "katex.min.css", SITE / "assets" / "katex" / "katex.min.css")
    for font in (KATEX_DIST / "fonts").glob("*.woff2"):
        shutil.copy2(font, SITE / "assets" / "katex" / "fonts" / font.name)

    version = hashlib.sha1((ROOT / "content.py").read_bytes())
    for f in sorted(STATIC.rglob("*")):
        if f.is_file():
            version.update(f.name.encode())
            version.update(f.read_bytes())
    version.update(b"katex-0.19.1")
    ver = version.hexdigest()[:10]

    if DOCX.exists():
        shutil.copy2(DOCX, SITE / "assets" / "math-cheatsheet.docx")

    fonts = sorted(p.name for p in (KATEX_DIST / "fonts").glob("*.woff2"))
    sw = (
        (STATIC / "sw.js")
        .read_text(encoding="utf-8")
        .replace("__VERSION__", ver)
        .replace(
            "__FONTS__",
            json.dumps([f"/assets/katex/fonts/{name}" for name in fonts]),
        )
    )
    (SITE / "sw.js").write_text(sw, encoding="utf-8")
    shutil.copy2(STATIC / "manifest.webmanifest", SITE / "manifest.webmanifest")

    (SITE / "assets" / "search.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    chips = "\n".join(
        f'<a class="chip" href="#{c["id"]}" data-ch="{c["id"]}">'
        f'<span>§{c["num"]}</span>{SHORT.get(c["num"], c["title"])}</a>'
        for c in chapters
    )
    rail = "\n".join(
        f'<a class="rail-link" href="#{c["id"]}" data-ch="{c["id"]}">'
        f'<span class="r-num">§{c["num"]}</span>'
        f'<span class="r-title">{esc(c["title"])}</span></a>'
        for c in chapters
    )

    doc_meta = getattr(mod, "DOC", {})
    sub = doc_meta.get("sub", "公式 · 判定 · 触发词").split("——")[0].strip()
    desc = f"考研数学二背诵小抄：{n_ch} 章 {n_topics} 节 {n_tables} 张表 {n_formulas} 条公式。只留公式、判定结论和触发词。"

    page = f"""<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>数学小抄 · 数二背诵版</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#FCFCFA">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/assets/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/icon-180.png">
<link rel="preload" href="/assets/katex/fonts/KaTeX_Main-Regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/katex/fonts/KaTeX_Math-Italic.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/katex/katex.min.css">
<link rel="stylesheet" href="/assets/style.css?v={ver}">
<script>try{{var t=new URLSearchParams(location.search).get('theme');if(t!=='light'&&t!=='dark')t=localStorage.getItem('sx.theme');if(!t)t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
<a class="skip" href="#main">跳到正文</a>

<header class="topbar">
  <div class="bar-inner">
    <a class="bar-title" href="#top">数学小抄<span>数二</span></a>
    <nav class="chips" aria-label="章节">{chips}</nav>
    <div class="bar-tools">
      <span class="bar-count" title="已背小节"><b id="doneCount">0</b><i>/{n_topics}</i></span>
      <button class="icon-btn" id="quizBtn" type="button" aria-pressed="false" aria-label="自测模式" title="自测模式：遮住公式">{ICONS['hide']}{ICONS['show']}</button>
      <button class="icon-btn" id="themeBtn" type="button" aria-label="切换深色模式" title="切换深色模式">{ICONS['moon']}{ICONS['sun']}</button>
      <button class="icon-btn" id="searchBtn" type="button" aria-label="搜索" title="搜索（/）">{ICONS['search']}</button>
    </div>
  </div>
  <div class="bar-progress"><i id="progressBar"></i></div>
</header>

<section class="cover" id="top">
  <div class="cover-grid">
    <div class="cover-copy">
      <p class="cover-kicker">数二背诵版　2026</p>
      <p class="cover-lede">{esc(sub)}</p>
      <p class="cover-line">合上能复述，才算会。</p>
      <button class="cover-search" id="coverSearch" type="button">
        {ICONS['search']}<span>搜公式、判定或触发词</span><kbd>/</kbd>
      </button>
      <p class="cover-stats">{n_ch} 章　{n_topics} 节　{n_tables} 表　{n_formulas} 条公式</p>
    </div>
    <h1 class="cover-title">数学小抄</h1>
  </div>
</section>

<div class="layout">
  <aside class="rail">
    <nav aria-label="章节目录">{rail}</nav>
    <div class="rail-progress">
      <div class="rp-top"><span>背诵进度</span><b><span id="doneCount2">0</span>/{n_topics}</b></div>
      <div class="rp-bar"><i id="progressBar2"></i></div>
      <button class="linkish" id="resetBtn" type="button">重置进度</button>
    </div>
  </aside>

  <main class="book" id="main">
{body}
  </main>
</div>

<footer class="foot">
  <div class="foot-inner">
    <p class="foot-strong">数学小抄　数二背诵版</p>
    <p>{n_ch} 章　{n_topics} 节　{n_tables} 张表　{n_formulas} 条公式　｜　构建于 {time.strftime('%Y-%m-%d')}</p>
    <p>内容源 <code>content.py</code>　·　<a href="/assets/math-cheatsheet.docx" download="数学小抄_数二背诵版.docx">下载打印版（Word）</a></p>
  </div>
</footer>

<div class="search-layer" id="searchLayer" hidden>
  <div class="search-panel" role="dialog" aria-modal="true" aria-label="搜索小抄">
    <div class="search-box">
      {ICONS['search']}
      <input id="searchInput" type="search" placeholder="搜公式、判定或触发词…" autocomplete="off" spellcheck="false" aria-label="搜索关键词">
      <button class="s-close" id="searchClose" type="button" aria-label="关闭搜索">{ICONS['close']}</button>
    </div>
    <p class="s-meta" id="searchMeta">输入关键词，例如「双纽线」「法线」「罗尔」</p>
    <div class="s-results" id="searchResults"></div>
    <p class="s-foot">↑↓ 选择　Enter 跳转　Esc 关闭</p>
  </div>
</div>

<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script src="/assets/app.js?v={ver}" defer></script>
</body>
</html>
"""

    out = SITE / "index.html"
    out.write_text(page, encoding="utf-8")
    gz = gzip.compress(page.encode("utf-8"), 9)
    print(
        f"章节 {n_ch} · 小节 {n_topics} · 表格 {n_tables} · 公式 {n_formulas}"
        f"（预渲染 {rendered_count} 个片段）"
    )
    print(f"index.html {human_size(out.stat().st_size)} · gzip {human_size(len(gz))}")
    print(f"输出：{SITE}")
    print(f"用时 {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
