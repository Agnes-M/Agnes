#!/usr/bin/env python3
"""Generate a print-friendly vocabulary dictation sheet from a source PDF."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz

CHINESE_FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
LATIN_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

PAGE_MARKER = re.compile(r"^--\s*\d+\s+of\s+\d+\s*--$")
ENGLISH_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9()\-]*\.?")
ENGLISH_PAREN = re.compile(r"\([A-Za-z][A-Za-z0-9/\s]*\)")
ENTRY_HEAD = re.compile(
    r"^(\d+)\.(?:\d+\.)?\s*([A-Za-z][A-Za-z0-9()\-]*)(?:\s+(.+))?$"
)


@dataclass(frozen=True)
class VocabEntry:
    number: int
    english: str
    chinese: str


def extract_lines(pdf_path: Path) -> list[str]:
    doc = fitz.open(pdf_path)
    lines: list[str] = []
    try:
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                for line in block["lines"]:
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    if text and not PAGE_MARKER.match(text):
                        lines.append(text)
    finally:
        doc.close()
    return lines


def clean_chinese(text: str) -> str:
    text = ENGLISH_PAREN.sub("", text)
    parts = ENGLISH_TOKEN.split(text)
    cleaned: list[str] = []
    for part in parts:
        fragment = part.strip(" \t;；,，()（）")
        if fragment:
            cleaned.append(fragment)
    if not cleaned:
        return ""

    merged = [cleaned[0]]
    for fragment in cleaned[1:]:
        if fragment != merged[-1]:
            merged.append(fragment)
    result = "；".join(merged)
    result = re.sub(r"[;；]{2,}", "；", result)
    result = re.sub(r"[()（）]+$", "", result)
    return result


def parse_entries(lines: list[str]) -> list[VocabEntry]:
    entries: list[VocabEntry] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if line.startswith("高考"):
            index += 1
            continue

        match = ENTRY_HEAD.match(line)
        if not match:
            index += 1
            continue

        number = int(match.group(1))
        english = match.group(2)
        inline_chinese = match.group(3)
        chinese_parts: list[str] = []

        if inline_chinese:
            chinese_parts.append(inline_chinese)
        else:
            index += 1
            while index < len(lines) and not ENTRY_HEAD.match(lines[index]):
                chinese_parts.append(lines[index])
                index += 1

        chinese = clean_chinese(" ".join(chinese_parts))
        entries.append(VocabEntry(number=number, english=english, chinese=chinese))
        if inline_chinese:
            index += 1

    entries.sort(key=lambda item: item.number)
    return entries


def wrap_chinese(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [text]


def generate_dictation_pdf(
    entries: list[VocabEntry],
    output_pdf: Path,
    *,
    title: str = "高考英语核心高频 688 个词汇 · 默写练习",
    entries_per_page: int = 48,
) -> None:
    doc = fitz.open()
    page_width, page_height = fitz.paper_size("a4")
    margin_x = 42
    margin_top = 48
    margin_bottom = 42
    column_gap = 24
    usable_width = page_width - margin_x * 2
    column_width = (usable_width - column_gap) / 2
    columns_per_page = 2
    rows_per_column = entries_per_page // columns_per_page
    row_height = 28
    header_height = 56

    def new_page(page_index: int) -> fitz.Page:
        page = doc.new_page(width=page_width, height=page_height)
        page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
        page.insert_font(fontname="latin", fontfile=LATIN_FONT)

        page.insert_text(
            (margin_x, margin_top),
            title,
            fontname="zh",
            fontsize=15,
            color=(0.12, 0.12, 0.12),
        )
        page.insert_text(
            (page_width - margin_x - 70, margin_top - 2),
            f"第 {page_index} 页",
            fontname="zh",
            fontsize=9,
            color=(0.45, 0.45, 0.45),
        )
        page.draw_line(
            (margin_x, margin_top + 10),
            (page_width - margin_x, margin_top + 10),
            color=(0.82, 0.82, 0.82),
            width=0.8,
        )
        page.insert_text(
            (margin_x, margin_top + 24),
            "序号",
            fontname="zh",
            fontsize=8,
            color=(0.5, 0.5, 0.5),
        )
        page.insert_text(
            (margin_x + 28, margin_top + 24),
            "默写（英文）",
            fontname="zh",
            fontsize=8,
            color=(0.5, 0.5, 0.5),
        )
        page.insert_text(
            (margin_x + 188, margin_top + 24),
            "中文释义",
            fontname="zh",
            fontsize=8,
            color=(0.5, 0.5, 0.5),
        )

        second_header_x = margin_x + column_width + column_gap
        page.insert_text(
            (second_header_x, margin_top + 24),
            "序号",
            fontname="zh",
            fontsize=8,
            color=(0.5, 0.5, 0.5),
        )
        page.insert_text(
            (second_header_x + 28, margin_top + 24),
            "默写（英文）",
            fontname="zh",
            fontsize=8,
            color=(0.5, 0.5, 0.5),
        )
        page.insert_text(
            (second_header_x + 188, margin_top + 24),
            "中文释义",
            fontname="zh",
            fontsize=8,
            color=(0.5, 0.5, 0.5),
        )
        return page

    page_number = 1
    page = new_page(page_number)
    start_y = margin_top + header_height

    for entry_index, entry in enumerate(entries):
        slot = entry_index % entries_per_page
        if slot == 0 and entry_index > 0:
            page_number += 1
            page = new_page(page_number)
        column = slot // rows_per_column
        row = slot % rows_per_column
        x0 = margin_x + column * (column_width + column_gap)
        y = start_y + row * row_height

        number_text = f"{entry.number:>3}."
        page.insert_text(
            (x0, y),
            number_text,
            fontname="latin",
            fontsize=9,
            color=(0.2, 0.2, 0.2),
        )

        blank_x0 = x0 + 28
        blank_x1 = x0 + 176
        page.draw_line(
            (blank_x0, y + 4),
            (blank_x1, y + 4),
            color=(0.45, 0.45, 0.45),
            width=0.8,
        )
        page.insert_text(
            (blank_x1 - 34, y - 1),
            "英文",
            fontname="zh",
            fontsize=6.5,
            color=(0.72, 0.72, 0.72),
        )

        chinese_x = x0 + 184
        chinese_lines = wrap_chinese(entry.chinese, max_chars=14)
        line_count = min(len(chinese_lines), 2)
        chinese_font_size = 8.2 if line_count == 1 and len(entry.chinese) <= 16 else 7.4
        for line_offset in range(line_count):
            page.insert_text(
                (chinese_x, y - 1 + line_offset * 10),
                chinese_lines[line_offset],
                fontname="zh",
                fontsize=chinese_font_size,
                color=(0.15, 0.15, 0.15),
            )

        if row < rows_per_column - 1:
            divider_y = y + 12
            page.draw_line(
                (x0, divider_y),
                (x0 + column_width - 6, divider_y),
                color=(0.92, 0.92, 0.92),
                width=0.4,
            )

    last_page = doc[-1]
    last_page.insert_text(
        (margin_x, page_height - margin_bottom + 12),
        f"共 {len(entries)} 个词汇 · 建议对照中文释义默写英文单词",
        fontname="zh",
        fontsize=8,
        color=(0.55, 0.55, 0.55),
    )

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_pdf, garbage=4, deflate=True)
    doc.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从词汇 PDF 生成排版美观、适合打印默写的练习册。"
    )
    parser.add_argument("input", type=Path, help="输入词汇 PDF")
    parser.add_argument("output", type=Path, help="输出默写练习 PDF")
    parser.add_argument(
        "--entries-per-page",
        type=int,
        default=48,
        help="每页词条数（默认 48，双栏排版）",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()

    if not input_path.exists():
        parser.error(f"输入文件不存在: {input_path}")

    lines = extract_lines(input_path)
    entries = parse_entries(lines)
    if not entries:
        parser.error("未能从 PDF 中解析出任何词汇。")

    generate_dictation_pdf(
        entries,
        output_path,
        entries_per_page=args.entries_per_page,
    )
    print(f"[OK] 已生成 {len(entries)} 个词条 -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
