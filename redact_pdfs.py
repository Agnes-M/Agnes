from __future__ import annotations

import argparse
import re
import sys
import unicodedata
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
class LineCharMap:
    char: str
    index: int
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


def iter_line_maps(page: fitz.Page) -> Iterator[tuple[str, list[LineCharMap]]]:
    page_dict = page.get_text("rawdict")
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            chars: list[LineCharMap] = []
            parts: list[str] = []
            for span in line.get("spans", []):
                for char_data in span.get("chars", []):
                    char = char_data.get("c", "")
                    if not char:
                        continue
                    chars.append(
                        LineCharMap(
                            char=char,
                            index=len(parts),
                            rect=fitz.Rect(char_data["bbox"]),
                        )
                    )
                    parts.append(char)

            line_text = "".join(parts)
            if chars and line_text.strip():
                yield line_text, chars


def normalize_with_index_map(text: str) -> tuple[str, list[int]]:
    normalized_chars: list[str] = []
    index_map: list[int] = []
    for original_index, char in enumerate(text):
        normalized = unicodedata.normalize("NFKC", char)
        for normalized_char in normalized:
            normalized_chars.append(normalized_char)
            index_map.append(original_index)
    return "".join(normalized_chars), index_map


def iter_sensitive_ranges(
    line_text: str, rules: Sequence[RedactionRule] = DEFAULT_RULES
) -> Iterator[tuple[str, int, int]]:
    normalized_line, index_map = normalize_with_index_map(line_text)
    seen: set[tuple[str, int, int]] = set()
    for rule in rules:
        for pattern in rule.patterns:
            for match in pattern.finditer(normalized_line):
                normalized_start, normalized_end = match.span("value")
                if normalized_start == normalized_end:
                    continue

                start = index_map[normalized_start]
                end = index_map[normalized_end - 1] + 1
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


def rects_for_range(
    chars: Sequence[LineCharMap], range_start: int, range_end: int
) -> list[fitz.Rect]:
    relevant = [
        char.rect
        for char in chars
        if range_start <= char.index < range_end and char.char.strip()
    ]
    if not relevant:
        return []

    combined = fitz.Rect(relevant[0])
    for rect in relevant[1:]:
        combined.include_rect(rect)

    padding = 0.6
    combined = fitz.Rect(
        combined.x0 - padding,
        combined.y0 - 0.5,
        combined.x1 + padding,
        combined.y1 + 0.5,
    )
    return [combined]


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
