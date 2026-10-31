#!/usr/bin/env bash
# 全量构建：Word 小抄 + 静态网页
set -euo pipefail
cd "$(dirname "$0")"

echo "==> 构建 Word 小抄"
uv run --no-project --with python-docx python -B build_数学小抄_数二背诵版.py

echo "==> 自检 Word 小抄"
uv run --no-project --with python-docx python -B check_docx.py 数学小抄_数二背诵版.docx

echo "==> 构建静态网页"
python3 -B web/build.py
