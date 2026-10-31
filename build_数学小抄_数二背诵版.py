# -*- coding: utf-8 -*-
"""生成《数学小抄_数二背诵版.docx》。

流程：扫 content.py 里的 $公式$ → 一次性 LaTeX 渲染成 PNG → python-docx 排版。
运行：cd "…/数学小抄" && uv run --no-project --with python-docx python -B build_数学小抄_数二背诵版.py
"""
import re
import sys

import content
import mathimg
import xc_lib as X

FORMULA = re.compile(r"\$([^$]+)\$")
OUT = "数学小抄_数二背诵版.docx"


def lines_of(text):
    return str(text).split("\n")


def scan():
    regs = []
    for kind, payload in content.BLOCKS:
        if kind == "T":
            for cell in payload.get("head", []):
                for line in lines_of(cell):
                    regs += inline_of(line)
            for row in payload["rows"]:
                for cell in row:
                    for line in lines_of(cell):
                        s = line.strip()
                        m = FORMULA.fullmatch(s)
                        if m:
                            regs.append((m.group(1), "block"))
                        else:
                            regs += inline_of(s)
        else:
            regs += inline_of(payload)
    seen, out = set(), []
    for latex, style in regs:
        k = (latex.strip(), style)
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def inline_of(text):
    m = FORMULA.fullmatch(str(text).strip())
    if m:
        return [(m.group(1), "block")]
    return [(x, "inline") for x in FORMULA.findall(str(text))]


def build():
    regs = scan()
    bank = mathimg.MathBank()
    bank.register(regs)
    print("公式数：", len(regs))
    bank.build()
    X.BANK = bank
    print("渲染完成")

    doc = X.init_doc(content.DOC["subject"])
    X.title_block(doc, content.DOC["main"], content.DOC["sub"],
                  content.DOC["meta"], content.DOC["usage"])
    for kind, payload in content.BLOCKS:
        if kind == "S":
            X.section(doc, payload)
        elif kind == "H":
            X.sub(doc, payload)
        elif kind == "P":
            X.para(doc, payload)
        elif kind == "N":
            X.note(doc, payload)
        elif kind == "T":
            X.make_table(doc, **payload)
        else:
            raise ValueError(kind)
    X.save(doc, OUT)


if __name__ == "__main__":
    build()
