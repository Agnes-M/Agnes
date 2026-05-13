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


FIELD_STOP_PATTERN = r"(?=(?:\s{2,}|[|｜]|(?:[A-Za-z\u4e00-\u9fff]{1,8}\s*[:：]))|$)"


@dataclass(frozen=True)
class RedactionRule:
    field_name: str
    pattern: re.Pattern[str]


DEFAULT_RULES: tuple[RedactionRule, ...] = (
    RedactionRule(
        "姓名",
        re.compile(
            rf"(?P<label>(?:患者)?姓名)\s*[:：]?\s*(?P<value>.+?){FIELD_STOP_PATTERN}"
        ),
    ),
    RedactionRule(
        "年龄",
        re.compile(r"(?P<label>年龄)\s*[:：]?\s*(?P<value>\d+\s*(?:岁|月)?)"),
    ),
    RedactionRule(
        "送检医生",
        re.compile(
            rf"(?P<label>送检医生|送检医师)\s*[:：]?\s*(?P<value>.+?){FIELD_STOP_PATTERN}"
        ),
    ),
    RedactionRule(
        "送检单位",
        re.compile(
            rf"(?P<label>送检单位)\s*[:：]?\s*(?P<value>.+?){FIELD_STOP_PATTERN}"
        ),
    ),
)


def iter_line_chars(page: fitz.Page) -> Iterable[list[dict]]:
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


def expand_rect(rect: fitz.Rect, margin: float = 0.8) -> fitz.Rect:
    return fitz.Rect(rect.x0 - margin, rect.y0 - margin, rect.x1 + margin, rect.y1 + margin)


def rect_for_range(chars: Sequence[dict], start: int, end: int) -> fitz.Rect | None:
    selected = chars[start:end]
    if not selected:
        return None

    non_whitespace = [fitz.Rect(char["bbox"]) for char in selected if char["c"].strip()]
    rects = non_whitespace or [fitz.Rect(char["bbox"]) for char in selected]
    if not rects:
        return None

    rect = fitz.Rect(rects[0])
    for item in rects[1:]:
        rect |= item
    return expand_rect(rect)


def normalize_line(chars: Sequence[dict]) -> tuple[str, list[int]]:
    normalized_parts: list[str] = []
    normalized_to_original: list[int] = []

    for index, char in enumerate(chars):
        normalized_char = unicodedata.normalize("NFKC", char["c"])
        if not normalized_char:
            continue
        normalized_parts.append(normalized_char)
        normalized_to_original.extend([index] * len(normalized_char))

    return "".join(normalized_parts), normalized_to_original


def original_range_from_normalized(
    mapping: Sequence[int], normalized_start: int, normalized_end: int
) -> tuple[int, int] | None:
    if normalized_start >= len(mapping) or normalized_end == 0:
        return None

    original_start = mapping[normalized_start]
    original_end = mapping[normalized_end - 1] + 1
    return original_start, original_end


def find_redaction_rects(page: fitz.Page, rules: Sequence[RedactionRule]) -> list[fitz.Rect]:
    rects: list[fitz.Rect] = []
    for chars in iter_line_chars(page):
        line_text, index_mapping = normalize_line(chars)
        for rule in rules:
            for match in rule.pattern.finditer(line_text):
                value = match.group("value").strip()
                if not value:
                    continue
                original_range = original_range_from_normalized(
                    index_mapping, match.start("value"), match.end("value")
                )
                if original_range is None:
                    continue
                rect = rect_for_range(chars, original_range[0], original_range[1])
                if rect is not None:
                    rects.append(rect)
    return rects


def redact_pdf(input_pdf: Path, output_pdf: Path, fill_color: tuple[float, float, float]) -> int:
    doc = fitz.open(input_pdf)
    total_redactions = 0

    try:
        for page in doc:
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
    parser = argparse.ArgumentParser(description="批量脱敏 PDF 中的姓名、年龄、送检医生、送检单位。")
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
        redaction_count = redact_pdf(source_pdf, target_pdf, fill_color)
        total_files += 1
        total_redactions += redaction_count
        print(f"[OK] {source_pdf} -> {target_pdf} (脱敏 {redaction_count} 处)")

    print(f"完成，共处理 {total_files} 个 PDF，脱敏 {total_redactions} 处。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
