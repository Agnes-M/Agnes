from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import fitz


COMMON_TERMINATORS = (
    "姓名",
    "患者姓名",
    "性别",
    "年龄",
    "送检医生",
    "送检单位",
    "送检科室",
    "标本类型",
    "样本类型",
    "病历号",
    "住院号",
    "门诊号",
    "临床诊断",
)


@dataclass(frozen=True)
class RedactionRule:
    name: str
    patterns: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class SpanCharMap:
    text: str
    start: int
    end: int
    rect: fitz.Rect


@dataclass(frozen=True)
class PdfResult:
    input_path: Path
    output_path: Path
    page_count: int
    redaction_count: int


def compile_patterns() -> tuple[RedactionRule, ...]:
    terminators = "|".join(re.escape(item) for item in COMMON_TERMINATORS)
    flags = re.UNICODE

    return (
        RedactionRule(
            name="name",
            patterns=(
                re.compile(
                    r"(?P<label>姓名|患者姓名)\s*[:：]?\s*(?P<value>[A-Za-z\u4e00-\u9fff·•]{1,20})",
                    flags,
                ),
            ),
        ),
        RedactionRule(
            name="age",
            patterns=(
                re.compile(
                    r"(?P<label>年龄)\s*[:：]?\s*(?P<value>\d{1,3}\s*(?:岁|Y|y|岁半)?)",
                    flags,
                ),
            ),
        ),
        RedactionRule(
            name="doctor",
            patterns=(
                re.compile(
                    rf"(?P<label>送检医生)\s*[:：]?\s*(?P<value>.+?)(?=\s*(?:{terminators})|$)",
                    flags,
                ),
            ),
        ),
        RedactionRule(
            name="institution",
            patterns=(
                re.compile(
                    rf"(?P<label>送检单位)\s*[:：]?\s*(?P<value>.+?)(?=\s*(?:{terminators})|$)",
                    flags,
                ),
            ),
        ),
    )


DEFAULT_RULES = compile_patterns()


def iter_pdf_files(input_path: Path) -> Iterator[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            raise ValueError(f"输入文件不是 PDF: {input_path}")
        yield input_path
        return

    if not input_path.is_dir():
        raise ValueError(f"输入路径不存在: {input_path}")

    for path in sorted(input_path.rglob("*")):
        if path.is_file() and path.suffix.lower() == ".pdf":
            yield path


def iter_line_maps(page: fitz.Page) -> Iterator[tuple[str, list[SpanCharMap]]]:
    page_dict = page.get_text("dict")
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans: list[SpanCharMap] = []
            cursor = 0
            parts: list[str] = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text:
                    continue
                start = cursor
                end = cursor + len(text)
                spans.append(
                    SpanCharMap(
                        text=text,
                        start=start,
                        end=end,
                        rect=fitz.Rect(span["bbox"]),
                    )
                )
                parts.append(text)
                cursor = end

            line_text = "".join(parts)
            if spans and line_text.strip():
                yield line_text, spans


def iter_sensitive_ranges(
    line_text: str, rules: Sequence[RedactionRule] = DEFAULT_RULES
) -> Iterator[tuple[str, int, int]]:
    seen: set[tuple[str, int, int]] = set()
    for rule in rules:
        for pattern in rule.patterns:
            for match in pattern.finditer(line_text):
                start, end = match.span("value")
                if start == end:
                    continue

                value = line_text[start:end]
                left_trim = len(value) - len(value.lstrip())
                right_trim = len(value) - len(value.rstrip())
                start += left_trim
                end -= right_trim
                if start >= end:
                    continue

                marker = (rule.name, start, end)
                if marker not in seen:
                    seen.add(marker)
                    yield marker


def slice_span_rect(
    rect: fitz.Rect, text: str, relative_start: int, relative_end: int
) -> fitz.Rect:
    if not text:
        return rect

    char_count = max(len(text), 1)
    width = rect.x1 - rect.x0
    if width <= 0:
        return rect

    char_width = width / char_count
    left = rect.x0 + (relative_start * char_width)
    right = rect.x0 + (relative_end * char_width)
    padding = min(max(char_width * 0.2, 0.4), 1.5)
    return fitz.Rect(
        max(rect.x0, left - padding),
        rect.y0 - 0.5,
        min(rect.x1, right + padding),
        rect.y1 + 0.5,
    )


def rects_for_range(
    spans: Sequence[SpanCharMap], range_start: int, range_end: int
) -> list[fitz.Rect]:
    rects: list[fitz.Rect] = []
    for span in spans:
        overlap_start = max(range_start, span.start)
        overlap_end = min(range_end, span.end)
        if overlap_start >= overlap_end:
            continue

        relative_start = overlap_start - span.start
        relative_end = overlap_end - span.start
        if not span.text[relative_start:relative_end].strip():
            continue

        rects.append(
            slice_span_rect(span.rect, span.text, relative_start, relative_end)
        )
    return rects


def unique_rects(rects: Iterable[fitz.Rect]) -> list[fitz.Rect]:
    unique: list[fitz.Rect] = []
    seen: set[tuple[float, float, float, float]] = set()
    for rect in rects:
        marker = (
            round(rect.x0, 2),
            round(rect.y0, 2),
            round(rect.x1, 2),
            round(rect.y1, 2),
        )
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(rect)
    return unique


def redact_pdf(
    input_path: Path,
    output_path: Path,
    rules: Sequence[RedactionRule] = DEFAULT_RULES,
) -> PdfResult:
    document = fitz.open(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_redactions = 0
    for page in document:
        page_rects: list[fitz.Rect] = []
        for line_text, spans in iter_line_maps(page):
            for _, start, end in iter_sensitive_ranges(line_text, rules):
                page_rects.extend(rects_for_range(spans, start, end))

        page_rects = unique_rects(page_rects)
        for rect in page_rects:
            page.add_redact_annot(rect, fill=(1, 1, 1))

        if page_rects:
            page.apply_redactions()
            total_redactions += len(page_rects)

    document.save(output_path, garbage=4, deflate=True)
    page_count = document.page_count
    document.close()
    return PdfResult(
        input_path=input_path,
        output_path=output_path,
        page_count=page_count,
        redaction_count=total_redactions,
    )


def build_output_path(source_path: Path, input_root: Path, output_root: Path) -> Path:
    if input_root.is_file():
        if output_root.suffix.lower() == ".pdf":
            return output_root
        return output_root / source_path.name

    return output_root / source_path.relative_to(input_root)


def process_paths(input_path: Path, output_path: Path) -> list[PdfResult]:
    results: list[PdfResult] = []
    for pdf_path in iter_pdf_files(input_path):
        destination = build_output_path(pdf_path, input_path, output_path)
        results.append(redact_pdf(pdf_path, destination))
    return results


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批量删除 PDF 中的姓名、年龄、送检医生、送检单位等敏感信息。"
    )
    parser.add_argument("input", help="输入 PDF 文件或目录")
    parser.add_argument("output", help="输出 PDF 文件或目录")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    try:
        results = process_paths(input_path, output_path)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    if not results:
        print("未找到任何 PDF 文件。", file=sys.stderr)
        return 1

    total_pages = sum(item.page_count for item in results)
    total_redactions = sum(item.redaction_count for item in results)
    for result in results:
        print(
            f"[OK] {result.input_path} -> {result.output_path} "
            f"(pages={result.page_count}, redactions={result.redaction_count})"
        )

    print(
        f"共处理 {len(results)} 个 PDF，{total_pages} 页，"
        f"执行 {total_redactions} 处脱敏。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
