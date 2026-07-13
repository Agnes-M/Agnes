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
LATIN_BOLD_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PAGE_MARKER = re.compile(r"^--\s*\d+\s+of\s+\d+\s*--$")
ENTRY_HEAD = re.compile(
    r"^(\d+)\.(?:\d+\.)?\s*([A-Za-z][A-Za-z0-9()\-]*)(?:\s+(.+))?$"
)

HEADER_BLUE = (0.184, 0.329, 0.588)
TITLE_BLUE = (0.18, 0.33, 0.58)
GRID_GRAY = (0.75, 0.75, 0.75)
TEXT_DARK = (0.1, 0.1, 0.1)
TEXT_MUTED = (0.45, 0.45, 0.45)
WHITE = (1, 1, 1)

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN_LEFT = 32
TABLE_RIGHT = 572
TABLE_TOP = 85
TABLE_BOTTOM = 740
COL_NUM = 24
COL_MEANING = 151
COL_BLANK = 95
BASE_ROW_HEIGHT = 24
LINE_HEIGHT = 12
MEANING_WRAP_CHARS = 22


@dataclass(frozen=True)
class VocabEntry:
    number: int
    english: str
    meaning: str


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


def format_meaning(parts: list[str]) -> str:
    meaning = "".join(parts)
    meaning = re.sub(r"\s+", " ", meaning).strip()
    return meaning


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
        inline_meaning = match.group(3)
        meaning_parts: list[str] = []

        if inline_meaning:
            meaning_parts.append(inline_meaning)
        else:
            index += 1
            while index < len(lines) and not ENTRY_HEAD.match(lines[index]):
                meaning_parts.append(lines[index])
                index += 1

        meaning = format_meaning(meaning_parts)
        entries.append(VocabEntry(number=number, english=english, meaning=meaning))
        if inline_meaning:
            index += 1

    entries.sort(key=lambda item: item.number)
    return entries


def wrap_meaning(text: str, max_chars: int = MEANING_WRAP_CHARS) -> list[str]:
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


def row_height_for_meaning(meaning: str) -> float:
    line_count = len(wrap_meaning(meaning))
    return BASE_ROW_HEIGHT + max(0, line_count - 1) * LINE_HEIGHT


def paginate_half(entries: list[VocabEntry]) -> list[list[VocabEntry]]:
    pages: list[list[VocabEntry]] = []
    current_page: list[VocabEntry] = []
    used_height = 0.0
    max_height = TABLE_BOTTOM - TABLE_TOP

    for entry in entries:
        height = row_height_for_meaning(entry.meaning)
        if current_page and used_height + height > max_height:
            pages.append(current_page)
            current_page = []
            used_height = 0.0
        current_page.append(entry)
        used_height += height

    if current_page:
        pages.append(current_page)
    return pages


def draw_table_header(page: fitz.Page, x0: float, y0: float, height: float) -> None:
    widths = [COL_NUM, COL_MEANING, COL_BLANK]
    labels = ["序\n号", "中文释义", "英文默写"]
    cursor = x0
    for width, label in zip(widths, labels):
        rect = fitz.Rect(cursor, y0, cursor + width, y0 + height)
        page.draw_rect(rect, color=HEADER_BLUE, fill=HEADER_BLUE)
        if "\n" in label:
            page.insert_text(
                (cursor + 7, y0 + 11),
                "序",
                fontname="zh",
                fontsize=9.5,
                color=WHITE,
            )
            page.insert_text(
                (cursor + 7, y0 + 22),
                "号",
                fontname="zh",
                fontsize=9.5,
                color=WHITE,
            )
        else:
            text_x = cursor + (14 if label == "中文释义" else 18)
            page.insert_text(
                (text_x, y0 + 17),
                label,
                fontname="zh",
                fontsize=9.5,
                color=WHITE,
            )
        cursor += width


def draw_vertical_grid(page: fitz.Page, x0: float, y0: float, y1: float) -> None:
    offsets = [0, COL_NUM, COL_NUM + COL_MEANING, COL_NUM + COL_MEANING + COL_BLANK]
    for offset in offsets:
        x = x0 + offset
        page.draw_line((x, y0), (x, y1), color=GRID_GRAY, width=0.48)


def draw_page_rows(
    page: fitz.Page,
    left_rows: list[VocabEntry],
    right_rows: list[VocabEntry],
) -> None:
    page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
    page.insert_font(fontname="latin", fontfile=LATIN_FONT)

    left_x = MARGIN_LEFT
    right_x = MARGIN_LEFT + COL_NUM + COL_MEANING + COL_BLANK
    header_height = 29.5
    body_top = TABLE_TOP + header_height
    row_count = max(len(left_rows), len(right_rows))

    row_heights: list[float] = []
    for row_index in range(row_count):
        left_entry = left_rows[row_index] if row_index < len(left_rows) else None
        right_entry = right_rows[row_index] if row_index < len(right_rows) else None
        left_height = row_height_for_meaning(left_entry.meaning) if left_entry else BASE_ROW_HEIGHT
        right_height = (
            row_height_for_meaning(right_entry.meaning) if right_entry else BASE_ROW_HEIGHT
        )
        row_heights.append(max(left_height, right_height))

    draw_table_header(page, left_x, TABLE_TOP, header_height)
    draw_table_header(page, right_x, TABLE_TOP, header_height)
    draw_vertical_grid(page, left_x, TABLE_TOP, TABLE_BOTTOM)
    draw_vertical_grid(page, right_x, TABLE_TOP, TABLE_BOTTOM)

    y = body_top
    for row_index in range(row_count):
        row_height = row_heights[row_index]
        y_bottom = y + row_height

        page.draw_line(
            (MARGIN_LEFT, y_bottom),
            (TABLE_RIGHT, y_bottom),
            color=GRID_GRAY,
            width=0.48,
        )

        for entry, block_x in ((left_rows[row_index] if row_index < len(left_rows) else None, left_x), (right_rows[row_index] if row_index < len(right_rows) else None, right_x)):
            if entry is None:
                continue

            page.insert_text(
                (block_x + 9, y + 9),
                str(entry.number),
                fontname="latin",
                fontsize=9.5,
                color=TEXT_DARK,
            )

            meaning_lines = wrap_meaning(entry.meaning)
            for line_offset, meaning_line in enumerate(meaning_lines):
                page.insert_text(
                    (block_x + COL_NUM + 4, y + 9 + line_offset * LINE_HEIGHT),
                    meaning_line,
                    fontname="zh",
                    fontsize=9.5,
                    color=TEXT_DARK,
                )

        y = y_bottom


def draw_title_page_header(page: fitz.Page) -> None:
    page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
    page.insert_font(fontname="latin", fontfile=LATIN_FONT)

    title = "高考英语核心高频688 词 · 中译英默写本"
    page.insert_textbox(
        fitz.Rect(36, 24, PAGE_WIDTH - 36, 48),
        title,
        fontname="zh",
        fontsize=16,
        color=TITLE_BLUE,
        align=fitz.TEXT_ALIGN_CENTER,
    )

    subtitle = "根据中文释义，在右侧空白处默写对应的英文单词（词性提示已保留）"
    page.insert_textbox(
        fitz.Rect(36, 48, PAGE_WIDTH - 36, 68),
        subtitle,
        fontname="zh",
        fontsize=9.5,
        color=TEXT_MUTED,
        align=fitz.TEXT_ALIGN_CENTER,
    )


def generate_dictation_pdf(
    entries: list[VocabEntry],
    output_pdf: Path,
) -> None:
    half = len(entries) // 2
    left_entries = entries[:half]
    right_entries = entries[half:]

    left_pages = paginate_half(left_entries)
    right_pages = paginate_half(right_entries)
    page_count = max(len(left_pages), len(right_pages))

    doc = fitz.open()
    try:
        for page_index in range(page_count):
            page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            draw_title_page_header(page)
            draw_page_rows(
                page,
                left_pages[page_index] if page_index < len(left_pages) else [],
                right_pages[page_index] if page_index < len(right_pages) else [],
            )

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_pdf, garbage=4, deflate=True)
    finally:
        doc.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从词汇 PDF 生成排版美观、适合打印默写的练习册。"
    )
    parser.add_argument("input", type=Path, help="输入词汇 PDF")
    parser.add_argument("output", type=Path, help="输出默写练习 PDF")
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

    generate_dictation_pdf(entries, output_path)
    print(f"[OK] 已生成 {len(entries)} 个词条 -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
