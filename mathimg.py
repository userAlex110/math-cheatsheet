# -*- coding: utf-8 -*-
"""LaTeX -> PNG 批量渲染（供数学小抄使用）。

为什么要图片而不是 OMML：
本机没有 Cambria Math，WPS 打开 OMML 公式时全部变成方框（实测），
LibreOffice 也吃不准。用 TeX 渲染成 600dpi PNG 后，WPS / LibreOffice / Word / 打印
四处一致，且可随表格缩放。

用法：
    from mathimg import MathBank
    bank = MathBank()                 # 自动扫描已登记公式
    bank.register([(latex, "block"), (latex, "inline")])
    bank.build()                      # 一次 latex + 一次 dvipng
    path, w_cm = bank.get(latex, "inline")
"""
import hashlib
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".mathcache")
DPI = 600
PT_PER_CM = 72 / 2.54

TEX_HEAD = r"""\documentclass[multi={math},border=2pt]{standalone}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{newtxmath}
\pagestyle{empty}
\begin{document}
"""
TEX_TAIL = r"\end{document}" + "\n"


def _key(latex, style):
    h = hashlib.sha1((style + "|" + latex).encode("utf-8")).hexdigest()[:16]
    return h


def _tex_for(latex, style):
    size = "9.4pt" if style == "block" else "8.8pt"
    if style == "block":
        body = r"\displaystyle \fontsize{%s}{12pt}\selectfont %s" % (size, latex)
    else:
        # 行内式：textstyle 让分式变小；\vphantom{(} 统一基线深度，避免行内图片高低不齐
        body = r"\textstyle \fontsize{%s}{10.5pt}\selectfont \vphantom{(} %s" % (size, latex)
    return "\\begin{math}%s\\end{math}\n" % body


class MathBank(object):
    def __init__(self):
        self.items = {}          # key -> (latex, style)
        self.paths = {}          # key -> png
        os.makedirs(CACHE, exist_ok=True)

    def register(self, pairs):
        for latex, style in pairs:
            latex = latex.strip()
            self.items[_key(latex, style)] = (latex, style)

    def build(self):
        todo = [k for k in self.items if not os.path.exists(os.path.join(CACHE, k + ".png"))]
        if not todo:
            return
        tex = [TEX_HEAD]
        for k in todo:
            latex, style = self.items[k]
            tex.append(_tex_for(latex, style))
        tex.append(TEX_TAIL)
        base = os.path.join(CACHE, "batch")
        with open(base + ".tex", "w", encoding="utf-8") as f:
            f.write("".join(tex))
        r = subprocess.run(["latex", "-interaction=nonstopmode", "-halt-on-error",
                            "batch.tex"], cwd=CACHE, capture_output=True, text=True)
        if r.returncode != 0:
            log = os.path.join(CACHE, "batch.log")
            tail = open(log, encoding="utf-8", errors="ignore").read()[-3000:] if os.path.exists(log) else r.stdout[-3000:]
            raise RuntimeError("latex 编译失败：\n" + tail)
        r = subprocess.run(["dvipng", "-D", str(DPI), "-bg", "Transparent",
                            "-o", "p%06d.png", "batch.dvi"],
                           cwd=CACHE, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("dvipng 失败：\n" + r.stdout[-2000:] + r.stderr[-2000:])
        pages = sorted(p for p in os.listdir(CACHE) if re.fullmatch(r"p\d{6}\.png", p))
        if len(pages) != len(todo):
            raise RuntimeError("页数不匹配：公式 %d 个，出图 %d 张" % (len(todo), len(pages)))
        for k, page in zip(todo, pages):
            src = os.path.join(CACHE, page)
            dst = os.path.join(CACHE, k + ".png")
            os.replace(src, dst)

    def get(self, latex, style="inline"):
        latex = latex.strip()
        for st in ([style, "block", "inline"] if style != "block" else ["block", "inline"]):
            p = os.path.join(CACHE, _key(latex, st) + ".png")
            if os.path.exists(p):
                w, h = png_size(p)
                return p, w / DPI * 2.54
        raise KeyError("未渲染的公式：" + latex)


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(26)
    w = int.from_bytes(head[16:20], "big")
    h = int.from_bytes(head[20:24], "big")
    return w, h
