#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from redact_pdf_batch import redact_pdf


INPUT_DIR = Path(r"C:\Users\lingy\Desktop\招标文件\报告清单\病理1-92")
OUTPUT_DIR = Path(r"C:\Users\lingy\Desktop\招标文件\报告清单\病理1-92_脱敏")

# 每个 PDF 最多处理前几页；如果想处理全部页面，改成 None
MAX_PAGES = 3

FILL_COLOR = (1, 1, 1)
OUTPUT_SUFFIX = "_脱敏"


def batch_redact() -> None:
    if not INPUT_DIR.exists():
        print(f"输入文件夹不存在：{INPUT_DIR}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(path for path in INPUT_DIR.glob("*.pdf") if path.is_file())

    if not pdf_files:
        print(f"没有找到 PDF 文件：{INPUT_DIR}")
        return

    success = 0
    fail = 0

    for index, pdf_file in enumerate(pdf_files, start=1):
        output_pdf = OUTPUT_DIR / f"{pdf_file.stem}{OUTPUT_SUFFIX}.pdf"
        print(f"\n[{index}/{len(pdf_files)}] 正在处理：{pdf_file.name}")

        try:
            redaction_count = redact_pdf(pdf_file, output_pdf, FILL_COLOR, MAX_PAGES)
            success += 1
            print(f"已完成：{output_pdf.name}（脱敏 {redaction_count} 处）")
        except Exception as error:
            fail += 1
            print(f"处理失败：{pdf_file.name}")
            print(f"错误原因：{error}")

    print(f"\n全部处理完成。成功：{success}，失败：{fail}")


if __name__ == "__main__":
    batch_redact()
