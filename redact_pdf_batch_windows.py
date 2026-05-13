#!/usr/bin/env python3
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import fitz


INPUT_DIR = Path(r"C:\Users\lingy\Desktop\招标文件\报告清单\病理1-92")
OUTPUT_DIR = Path(r"C:\Users\lingy\Desktop\招标文件\报告清单\病理1-92_脱敏")

# 每个 PDF 最多处理前几页；如果想处理全部页面，改成 None
MAX_PAGES = 3

FILL_COLOR = (1, 1, 1)
OUTPUT_SUFFIX = "_脱敏"

FIELD_SEPARATOR_PATTERN = r"\s{2,}|[|｜]"
SKIP_VALUES = frozenset({"/", "\\", "无"})
HEADER_MAX_X = 220
HEADER_MAX_Y = 90


@dataclass(frozen=True)
class RedactionRule:
    field_name: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class RuleMatch:
    field_name: str
    value: str
    rect: fitz.Rect


def compile_text_rule(field_name: str, label_pattern: str, stop_pattern: str) -> RedactionRule:
    return RedactionRule(
        field_name,
        re.compile(
            rf"(?P<label>{label_pattern})\s*[:：]?\s*(?P<value>.+?)(?=(?:{FIELD_SEPARATOR_PATTERN}|{stop_pattern})|$)"
        ),
    )


def compile_code_rule(field_name: str, label_pattern: str) -> RedactionRule:
    return RedactionRule(
        field_name,
        re.compile(rf"(?P<label>{label_pattern})\s*[:：]?\s*(?P<value>[A-Za-z0-9\-_\/]+)"),
    )


DEFAULT_RULES: tuple[RedactionRule, ...] = (
    compile_text_rule(
        "姓名",
        r"(?:患者)?姓\s*名",
        r"性\s*别(?:\s*[:：])?|门诊/住院号(?:\s*[:：])?|条形码(?:\s*[:：])?|报告编号(?:\s*[:：])?|公司条码(?:\s*[:：])?",
    ),
    RedactionRule(
        "年龄",
        re.compile(r"(?P<label>年龄)\s*[:：]?\s*(?P<value>\d+\s*(?:岁|月)?)"),
    ),
    compile_text_rule(
        "受检者",
        r"受检者",
        r"样本编号(?:\s*[:：])?",
    ),
    compile_code_rule("条形码", r"条形码"),
    compile_code_rule("公司条码", r"公司条码"),
    compile_code_rule("样本编号", r"样本编号"),
    compile_text_rule(
        "送检医生",
        r"送检医生",
        r"其他信息(?:\s*[:：])?|联系电话(?:\s*[:：])?|采集时间(?:\s*[:：])?|样本类型(?:\s*[:：])?|临床诊断(?:\s*[:：])?|检测结果(?:\s*[:：])?",
    ),
    compile_text_rule(
        "送检医师",
        r"送检医师",
        r"样本类型(?:\s*[:：])?|检测技术(?:\s*[:：])?|采样日期(?:\s*[:：])?|收样日期(?:\s*[:：])?|报告日期(?:\s*[:：])?|检测结果(?:\s*[:：])?",
    ),
    compile_text_rule(
        "送检单位",
        r"送检单位",
        r"送检医生(?:\s*[:：])?|送检医师(?:\s*[:：])?|送检科室(?:\s*[:：])?|样本类型(?:\s*[:：])?|临床诊断(?:\s*[:：])?|备注(?:\s*[:：])?|检验者(?:\s*[:：])?|审核者(?:\s*[:：])?|批准人(?:\s*[:：])?|检测结果(?:\s*[:：])?",
    ),
    compile_text_rule(
        "送检医院",
        r"送检医院",
        r"送检医生(?:\s*[:：])?|送检医师(?:\s*[:：])?|科室/病区(?:\s*[:：])?|门诊/住院号(?:\s*[:：])?|床号(?:\s*[:：])?|检测结果(?:\s*[:：])?",
    ),
)

HEADER_VALUE_RULES: tuple[RedactionRule, ...] = (
    compile_text_rule(
        "姓名",
        r"(?:患者)?姓\s*名|受检者",
        r"性\s*别(?:\s*[:：])?|门诊/住院号(?:\s*[:：])?|条形码(?:\s*[:：])?|报告编号(?:\s*[:：])?|报告号(?:\s*[:：])?",
    ),
    compile_code_rule("报告编号", r"报告编号|报告号"),
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


def line_rect(chars: Sequence[dict]) -> fitz.Rect | None:
    return rect_for_range(chars, 0, len(chars))


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


def should_redact_value(value: str) -> bool:
    cleaned = value.replace("\n", " ").strip()
    return bool(cleaned) and cleaned not in SKIP_VALUES


def normalize_value(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("\n", " ").strip()


def original_range_from_normalized(
    mapping: Sequence[int], normalized_start: int, normalized_end: int
) -> tuple[int, int] | None:
    if normalized_start >= len(mapping) or normalized_end == 0:
        return None

    original_start = mapping[normalized_start]
    original_end = mapping[normalized_end - 1] + 1
    return original_start, original_end


def is_header_line(rect: fitz.Rect | None) -> bool:
    return rect is not None and rect.x0 <= HEADER_MAX_X and rect.y0 <= HEADER_MAX_Y


def iter_rule_matches(
    page: fitz.Page,
    rules: Sequence[RedactionRule],
    *,
    header_only: bool = False,
) -> Iterable[RuleMatch]:
    for chars in iter_line_chars(page):
        current_line_rect = line_rect(chars)
        if header_only and not is_header_line(current_line_rect):
            continue

        line_text, index_mapping = normalize_line(chars)
        for rule in rules:
            for match in rule.pattern.finditer(line_text):
                value = normalize_value(match.group("value"))
                if not should_redact_value(value):
                    continue
                original_range = original_range_from_normalized(
                    index_mapping, match.start("value"), match.end("value")
                )
                if original_range is None:
                    continue
                rect = rect_for_range(chars, original_range[0], original_range[1])
                if rect is not None:
                    yield RuleMatch(rule.field_name, value, rect)


def find_redaction_rects(page: fitz.Page, rules: Sequence[RedactionRule]) -> list[fitz.Rect]:
    return [match.rect for match in iter_rule_matches(page, rules)]


def collect_header_targets(doc: fitz.Document, max_pages: int | None = None) -> set[str]:
    targets: set[str] = set()
    total_pages = len(doc)
    page_count = total_pages if max_pages is None else min(total_pages, max_pages)
    for page_index in range(page_count):
        page = doc[page_index]
        for match in iter_rule_matches(page, DEFAULT_RULES):
            if match.field_name in {"姓名", "受检者"}:
                targets.add(match.value)
        for match in iter_rule_matches(page, HEADER_VALUE_RULES, header_only=True):
            targets.add(match.value)
    return targets


def find_header_repeat_rects(page: fitz.Page, targets: set[str]) -> list[fitz.Rect]:
    normalized_targets = sorted(
        (normalize_value(target) for target in targets if should_redact_value(target)),
        key=len,
        reverse=True,
    )
    rects: list[fitz.Rect] = []

    for chars in iter_line_chars(page):
        current_line_rect = line_rect(chars)
        if not is_header_line(current_line_rect):
            continue

        line_text, index_mapping = normalize_line(chars)
        for target in normalized_targets:
            for match in re.finditer(re.escape(target), line_text):
                original_range = original_range_from_normalized(
                    index_mapping, match.start(), match.end()
                )
                if original_range is None:
                    continue
                rect = rect_for_range(chars, original_range[0], original_range[1])
                if rect is not None:
                    rects.append(rect)

    return rects


def redact_pdf(
    input_pdf: Path,
    output_pdf: Path,
    fill_color: tuple[float, float, float],
    max_pages: int | None = None,
) -> int:
    doc = fitz.open(input_pdf)
    total_redactions = 0

    try:
        total_pages = len(doc)
        page_count = total_pages if max_pages is None else min(total_pages, max_pages)
        header_targets = collect_header_targets(doc, max_pages)
        for page_index in range(page_count):
            page = doc[page_index]
            page_rects = find_redaction_rects(page, DEFAULT_RULES)
            page_rects.extend(find_header_repeat_rects(page, header_targets))
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
