#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz


DEFAULT_INPUT_DIR = Path(r"C:\Users\lingy\Desktop\招标文件\报告清单\病理1-92")
DEFAULT_OUTPUT_DIR = Path(r"C:\Users\lingy\Desktop\招标文件\报告清单\病理1-92_脱敏")
DEFAULT_MAX_PAGES = 3

STOP_FIELDS = (
    r"性\s*别",
    r"年龄",
    r"门诊/住院号",
    r"住院号",
    r"条形码",
    r"报告编号",
    r"公司条码",
    r"样本编号",
    r"送检单位",
    r"送检医院",
    r"送检医生",
    r"送检医师",
    r"送检科室",
    r"科室/病区",
    r"样本类型",
    r"检测技术",
    r"临床诊断",
    r"备注",
    r"检验者",
    r"审核者",
    r"批准人",
    r"其他信息",
    r"联系电话",
    r"采集时间",
    r"采样日期",
    r"收样日期",
    r"报告日期",
    r"床号",
)
STOP_PATTERN = rf"(?=\s*(?:{'|'.join(STOP_FIELDS)}|$))"


@dataclass(frozen=True)
class RedactionPattern:
    field_name: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class SourceChar:
    char: str
    bbox: fitz.Rect
    line_id: int


PATTERNS: tuple[RedactionPattern, ...] = (
    RedactionPattern(
        "姓名",
        re.compile(
            rf"(?P<label>(?:姓\s*名|受检者))\s*[:：]?\s*(?P<value>.+?){STOP_PATTERN}",
            re.S,
        ),
    ),
    RedactionPattern(
        "年龄",
        re.compile(r"(?P<label>年龄)\s*[:：]?\s*(?P<value>\d+\s*(?:岁|月)?)", re.S),
    ),
    RedactionPattern(
        "条码",
        re.compile(
            r"(?P<label>(?:条形码|公司条码|样本编号))\s*[:：]?\s*(?P<value>[A-Za-z0-9\-_ /]+)",
            re.S,
        ),
    ),
    RedactionPattern(
        "送检单位",
        re.compile(
            rf"(?P<label>(?:送检单位|送检医院))\s*[:：]?\s*(?P<value>.+?){STOP_PATTERN}",
            re.S,
        ),
    ),
    RedactionPattern(
        "送检医生",
        re.compile(
            rf"(?P<label>(?:送检医生|送检医师))\s*[:：]?\s*(?P<value>.+?){STOP_PATTERN}",
            re.S,
        ),
    ),
)


def normalize_fragment(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("：", ":").replace("\u00a0", " ").replace("\u3000", " ")
    return normalized


def iter_page_lines(page: fitz.Page) -> Iterable[list[dict]]:
    raw = page.get_text("rawdict")
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            chars: list[dict] = []
            for span in line.get("spans", []):
                chars.extend(span.get("chars", []))
            if chars:
                yield chars


def build_canonical_page_text(
    page: fitz.Page,
) -> tuple[str, list[int | None], list[SourceChar]]:
    canonical_parts: list[str] = []
    canonical_to_source: list[int | None] = []
    source_chars: list[SourceChar] = []
    previous_was_space = False

    for line_id, line_chars in enumerate(iter_page_lines(page)):
        for char in line_chars:
            source_index = len(source_chars)
            source_chars.append(
                SourceChar(char=char["c"], bbox=fitz.Rect(char["bbox"]), line_id=line_id)
            )

            normalized = normalize_fragment(char["c"])
            if not normalized:
                continue

            for normalized_char in normalized:
                if normalized_char.isspace():
                    if previous_was_space:
                        continue
                    normalized_char = " "
                canonical_parts.append(normalized_char)
                canonical_to_source.append(source_index)
                previous_was_space = normalized_char == " "

        if canonical_parts and not previous_was_space:
            canonical_parts.append(" ")
            canonical_to_source.append(None)
            previous_was_space = True

    return "".join(canonical_parts).strip(), canonical_to_source, source_chars


def trim_match_range(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def source_indexes_for_range(
    canonical_to_source: list[int | None], start: int, end: int
) -> list[int]:
    indexes = sorted(
        {
            source_index
            for source_index in canonical_to_source[start:end]
            if source_index is not None
        }
    )
    return indexes


def group_source_rects(source_chars: list[SourceChar], source_indexes: list[int]) -> list[fitz.Rect]:
    if not source_indexes:
        return []

    rects: list[fitz.Rect] = []
    current_rect: fitz.Rect | None = None
    current_line: int | None = None
    current_last_x1 = 0.0

    for source_index in source_indexes:
        source_char = source_chars[source_index]
        if not source_char.char.strip():
            continue

        rect = source_char.bbox
        should_split = (
            current_rect is None
            or current_line != source_char.line_id
            or rect.x0 - current_last_x1 > 10
        )

        if should_split:
            if current_rect is not None:
                rects.append(current_rect)
            current_rect = fitz.Rect(rect)
            current_line = source_char.line_id
        else:
            current_rect |= rect

        current_last_x1 = rect.x1

    if current_rect is not None:
        rects.append(current_rect)

    return [
        fitz.Rect(rect.x0 - 0.8, rect.y0 - 0.8, rect.x1 + 0.8, rect.y1 + 0.8) for rect in rects
    ]


def should_skip_value(value: str) -> bool:
    collapsed = re.sub(r"\s+", "", value)
    return not collapsed or collapsed in {"/", "\\", "无"}


def find_redaction_rects(page: fitz.Page) -> list[fitz.Rect]:
    canonical_text, canonical_to_source, source_chars = build_canonical_page_text(page)
    rects: list[fitz.Rect] = []

    for pattern in PATTERNS:
        for match in pattern.pattern.finditer(canonical_text):
            start, end = trim_match_range(canonical_text, match.start("value"), match.end("value"))
            value = canonical_text[start:end]
            if should_skip_value(value):
                continue

            source_indexes = source_indexes_for_range(canonical_to_source, start, end)
            rects.extend(group_source_rects(source_chars, source_indexes))

    return rects


def redact_one_pdf(
    input_pdf: Path,
    output_pdf: Path,
    max_pages: int | None = DEFAULT_MAX_PAGES,
    fill_color: tuple[float, float, float] = (1, 1, 1),
) -> int:
    doc = fitz.open(input_pdf)
    total_redactions = 0

    try:
        total_pages = len(doc)
        pages_to_process = total_pages if max_pages is None else min(total_pages, max_pages)

        for page_index in range(pages_to_process):
            page = doc[page_index]
            page_rects = find_redaction_rects(page)
            for rect in page_rects:
                page.add_redact_annot(rect, fill=fill_color, text="")
            if page_rects:
                page.apply_redactions()
                total_redactions += len(page_rects)

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_pdf, garbage=4, clean=True, deflate=True)
    finally:
        doc.close()

    return total_redactions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="批量脱敏病理/检验 PDF，避免使用 search_for 回搜字段值。"
    )
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT_DIR, help="输入目录")
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT_DIR, help="输出目录")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="每个 PDF 最多处理前几页；传 0 表示处理全部页面",
    )
    return parser


def batch_redact(input_dir: Path, output_dir: Path, max_pages: int | None) -> int:
    if not input_dir.exists():
        print(f"输入文件夹不存在：{input_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(input_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"没有找到 PDF 文件：{input_dir}")
        return 1

    success = 0
    fail = 0

    for index, pdf_file in enumerate(pdf_files, start=1):
        output_pdf = output_dir / f"{pdf_file.stem}_脱敏.pdf"
        print(f"\n[{index}/{len(pdf_files)}] 正在处理：{pdf_file.name}")

        try:
            redaction_count = redact_one_pdf(pdf_file, output_pdf, max_pages=max_pages)
            success += 1
            print(f"已完成：{output_pdf.name}，脱敏 {redaction_count} 处")
        except Exception as error:
            fail += 1
            print(f"处理失败：{pdf_file.name}")
            print(f"错误原因：{error}")

    print(f"\n全部处理完成。成功：{success}，失败：{fail}")
    return 0 if fail == 0 else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    max_pages = None if args.max_pages == 0 else args.max_pages
    return batch_redact(args.input.expanduser(), args.output.expanduser(), max_pages)


if __name__ == "__main__":
    sys.exit(main())
