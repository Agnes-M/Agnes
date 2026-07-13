#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import fitz


@dataclass(frozen=True)
class RedactionRule:
    field_name: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class PageChar:
    char: str
    bbox: tuple[float, float, float, float]
    line_id: int


DEFAULT_RULES: tuple[RedactionRule, ...] = (
    RedactionRule(
        "姓名",
        re.compile(
            r"(?P<label>姓\s*名|(?:患者)?姓名)\s*[:：]?\s*(?P<value>[^\n]*?)"
            r"(?=\s+(?:性\s*别|性别|门诊/住院号|病历号|病案号|条形码|报告编号|公司条码)|$)",
        ),
    ),
    RedactionRule(
        "受检者",
        re.compile(
            r"(?P<label>受检者)\s*[:：]?\s*(?P<value>[^\n]*?)(?=\s+样本编号|样本编号[:：]|$)"
        ),
    ),
    RedactionRule(
        "年龄",
        re.compile(r"(?P<label>年龄)\s*[:：]?\s*(?P<value>\d+\s*(?:岁|月)?)"),
    ),
    RedactionRule(
        "门诊住院号",
        re.compile(
            r"(?P<label>门诊/住院号|门诊号|住院号|病历号|病案号)\s*[:：]?\s*(?P<value>[A-Za-z0-9\-_/]+)"
        ),
    ),
    RedactionRule(
        "床号",
        re.compile(r"(?P<label>床号)\s*[:：]?\s*(?P<value>[A-Za-z0-9\-_/]+)"),
    ),
    RedactionRule(
        "条码编号",
        re.compile(r"(?P<label>条形码|公司条码|样本编号)\s*[:：]?\s*(?P<value>[A-Za-z0-9\-_/]+)"),
    ),
    RedactionRule(
        "送检医生",
        re.compile(
            r"(?P<label>送检医生|送检医师)\s*[:：]?\s*(?P<value>[^\n]*?)"
            r"(?=\s+(?:送检单位|送检医院|送检科室|其他信息|联系电话|采集时间|样本类型|样本编号|临床诊断|检测技术|采样日期|收样日期|报告日期)|$)",
        ),
    ),
    RedactionRule(
        "送检单位",
        re.compile(
            r"(?P<label>送检单位)\s*[:：]?\s*(?P<value>[^\n]*?)"
            r"(?=\s+(?:送检医生|送检医师|送检科室|样本类型|样本编号|临床诊断|备注|检验者|审核者|批准人)|$)",
        ),
    ),
    RedactionRule(
        "送检医院",
        re.compile(
            r"(?P<label>送检医院)\s*[:：]?\s*(?P<value>[^\n]*?)"
            r"(?=\s+(?:送检医生|送检医师|送检科室|科室/病区|门诊/住院号|床号)|$)",
        ),
    ),
    RedactionRule(
        "送检科室",
        re.compile(
            r"(?P<label>送检科室|科室/病区)\s*[:：]?\s*(?P<value>[^\n]*?)"
            r"(?=\s+(?:送检医生|送检医师|送检医院|门诊/住院号|床号|样本类型|样本编号|临床诊断|报告编号)|$)",
        ),
    ),
)


def iter_page_chars(page: fitz.Page) -> Iterable[PageChar]:
    raw = page.get_text("rawdict")
    line_id = 0
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    yield PageChar(char=char["c"], bbox=tuple(char["bbox"]), line_id=line_id)
            line_id += 1


def expand_rect(rect: fitz.Rect, margin: float = 0.8) -> fitz.Rect:
    return fitz.Rect(rect.x0 - margin, rect.y0 - margin, rect.x1 + margin, rect.y1 + margin)


def clean_value(value: str) -> str:
    return value.replace("\n", " ").strip()


def should_skip_value(value: str) -> bool:
    return not value or value in {"/", "\\", "无"}


def rect_for_chars(chars: Sequence[PageChar]) -> fitz.Rect | None:
    selected = list(chars)
    if not selected:
        return None

    non_whitespace = [fitz.Rect(char.bbox) for char in selected if char.char.strip()]
    rects = non_whitespace or [fitz.Rect(char.bbox) for char in selected]
    if not rects:
        return None

    rect = fitz.Rect(rects[0])
    for item in rects[1:]:
        rect |= item
    return expand_rect(rect)


def normalize_page_chars(chars: Sequence[PageChar]) -> tuple[str, list[int | None]]:
    normalized_parts: list[str] = []
    normalized_to_original: list[int | None] = []

    for index, char in enumerate(chars):
        if index and chars[index - 1].line_id != char.line_id:
            normalized_parts.append("\n")
            normalized_to_original.append(None)
        normalized_char = unicodedata.normalize("NFKC", char.char)
        if not normalized_char:
            continue
        normalized_parts.append(normalized_char)
        normalized_to_original.extend([index] * len(normalized_char))

    return "".join(normalized_parts), normalized_to_original


def original_indices_from_normalized(
    mapping: Sequence[int | None], normalized_start: int, normalized_end: int
) -> list[int]:
    if normalized_start >= len(mapping) or normalized_end == 0:
        return []

    indices: list[int] = []
    for mapped_index in mapping[normalized_start:normalized_end]:
        if mapped_index is None:
            continue
        if not indices or indices[-1] != mapped_index:
            indices.append(mapped_index)
    return indices


def rects_for_original_indices(chars: Sequence[PageChar], indices: Sequence[int]) -> list[fitz.Rect]:
    rects: list[fitz.Rect] = []
    current_line_id: int | None = None
    current_chars: list[PageChar] = []

    for index in indices:
        char = chars[index]
        if current_line_id is None or char.line_id == current_line_id:
            current_chars.append(char)
            current_line_id = char.line_id
            continue

        rect = rect_for_chars(current_chars)
        if rect is not None:
            rects.append(rect)
        current_chars = [char]
        current_line_id = char.line_id

    rect = rect_for_chars(current_chars)
    if rect is not None:
        rects.append(rect)

    return rects


def dedupe_rects(rects: Sequence[fitz.Rect]) -> list[fitz.Rect]:
    unique_rects: list[fitz.Rect] = []
    seen: set[tuple[float, float, float, float]] = set()

    for rect in rects:
        key = (round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2))
        if key in seen:
            continue
        seen.add(key)
        unique_rects.append(rect)

    return unique_rects


def find_redaction_rects(page: fitz.Page, rules: Sequence[RedactionRule]) -> list[fitz.Rect]:
    chars = list(iter_page_chars(page))
    if not chars:
        return []

    page_text, index_mapping = normalize_page_chars(chars)
    rects: list[fitz.Rect] = []

    for rule in rules:
        for match in rule.pattern.finditer(page_text):
            value = clean_value(match.group("value"))
            if should_skip_value(value):
                continue
            original_indices = original_indices_from_normalized(
                index_mapping, match.start("value"), match.end("value")
            )
            rects.extend(rects_for_original_indices(chars, original_indices))

    return dedupe_rects(rects)


def redact_pdf(
    input_pdf: Path,
    output_pdf: Path,
    fill_color: tuple[float, float, float],
    max_pages: int | None = None,
) -> int:
    doc = fitz.open(input_pdf)
    total_redactions = 0

    try:
        pages_to_process = len(doc) if max_pages is None else min(len(doc), max_pages)
        for page_index in range(pages_to_process):
            page = doc[page_index]
            page_rects = find_redaction_rects(page, DEFAULT_RULES)
            for rect in page_rects:
                page.add_redact_annot(rect, fill=fill_color, text="")
            if page_rects:
                page.apply_redactions()
                total_redactions += len(page_rects)

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_pdf, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()

    return total_redactions


def collect_pdf_files(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            raise ValueError(f"输入文件不是 PDF: {input_path}")
        return [input_path]

    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(path for path in input_path.glob(pattern) if path.is_file())


def resolve_output_path(
    source_pdf: Path, input_path: Path, output_path: Path, suffix: str
) -> Path:
    if input_path.is_file():
        if output_path.suffix.lower() == ".pdf":
            return output_path
        return output_path / f"{source_pdf.stem}{suffix}.pdf"

    relative = source_pdf.relative_to(input_path)
    return output_path / relative.with_name(f"{relative.stem}{suffix}.pdf")


def parse_fill_color(name: str) -> tuple[float, float, float]:
    colors = {
        "white": (1, 1, 1),
        "black": (0, 0, 0),
    }
    try:
        return colors[name]
    except KeyError as error:
        raise ValueError(f"不支持的填充颜色: {name}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="批量脱敏 PDF 中的患者隐私字段，适用于英夫利昔耐药检测等检验报告。"
    )
    parser.add_argument("input", type=Path, help="输入 PDF 文件或目录")
    parser.add_argument("output", type=Path, help="输出 PDF 文件或目录")
    parser.add_argument("--recursive", action="store_true", help="递归扫描输入目录")
    parser.add_argument(
        "--suffix",
        default="_redacted",
        help="输出文件名后缀，默认: _redacted",
    )
    parser.add_argument(
        "--fill-color",
        choices=("white", "black"),
        default="white",
        help="脱敏覆盖颜色，默认: white",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="每个 PDF 最多处理前几页；默认处理全部页面",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()

    if not input_path.exists():
        parser.error(f"输入路径不存在: {input_path}")

    pdf_files = collect_pdf_files(input_path, recursive=args.recursive)
    if not pdf_files:
        parser.error("未找到任何 PDF 文件。")

    fill_color = parse_fill_color(args.fill_color)
    total_files = 0
    total_redactions = 0

    for source_pdf in pdf_files:
        target_pdf = resolve_output_path(source_pdf, input_path, output_path, args.suffix)
        redaction_count = redact_pdf(
            source_pdf,
            target_pdf,
            fill_color,
            max_pages=args.max_pages,
        )
        total_files += 1
        total_redactions += redaction_count
        print(f"[OK] {source_pdf} -> {target_pdf} (脱敏 {redaction_count} 处)")

    print(f"完成，共处理 {total_files} 个 PDF，脱敏 {total_redactions} 处。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
