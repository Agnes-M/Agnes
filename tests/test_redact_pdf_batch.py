from __future__ import annotations

import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

import fitz


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "redact_pdf_batch.py"
CHINESE_FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"


def create_sample_pdf(pdf_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
    page.insert_text(
        (72, 96),
        "姓名：张三  性别：男  年龄：45岁",
        fontname="zh",
        fontsize=14,
    )
    page.insert_text(
        (72, 126),
        "送检医生：李医生  送检单位：某某医院检验科",
        fontname="zh",
        fontsize=14,
    )
    page.insert_text(
        (72, 156),
        "报告编号：RPT-001",
        fontname="zh",
        fontsize=14,
    )
    doc.save(pdf_path)
    doc.close()


def create_extended_pdf(pdf_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
    lines = (
        "姓名：张三  性别：男  门诊/住院号：ZY-001",
        "受检者：李四  样本编号：YP-123",
        "条形码：BC-777  公司条码：COMP-888",
        "送检单位：某某医院病理科  送检医生：王医生",
        "送检医院：第一人民医院  科室/病区：外科",
        "送检医师：赵主任  报告日期：2026-05-13",
    )
    y = 96
    for line in lines:
        page.insert_text((72, y), line, fontname="zh", fontsize=14)
        y += 28
    doc.save(pdf_path)
    doc.close()


def create_multi_page_pdf(pdf_path: Path) -> None:
    doc = fitz.open()
    first_page = doc.new_page()
    first_page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
    first_page.insert_text(
        (72, 96),
        "姓名：第一页患者  性别：男",
        fontname="zh",
        fontsize=14,
    )

    second_page = doc.new_page()
    second_page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
    second_page.insert_text(
        (72, 96),
        "姓名：第二页患者  性别：女",
        fontname="zh",
        fontsize=14,
    )
    doc.save(pdf_path)
    doc.close()


class PdfRedactionCliTests(unittest.TestCase):
    def test_cli_redacts_target_fields_and_keeps_other_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            input_dir = base / "input"
            output_dir = base / "output"
            input_dir.mkdir()

            source_pdf = input_dir / "report.pdf"
            create_sample_pdf(source_pdf)

            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(input_dir), str(output_dir)],
                check=True,
                capture_output=True,
                text=True,
            )

            output_pdf = output_dir / "report_redacted.pdf"
            self.assertTrue(output_pdf.exists(), result.stdout)

            doc = fitz.open(output_pdf)
            redacted_text = "\n".join(page.get_text() for page in doc)
            doc.close()
            redacted_text = unicodedata.normalize("NFKC", redacted_text)

            self.assertIn("姓名", redacted_text)
            self.assertIn("年龄", redacted_text)
            self.assertIn("送检医生", redacted_text)
            self.assertIn("送检单位", redacted_text)
            self.assertIn("性别:男", redacted_text)
            self.assertIn("报告编号:RPT-001", redacted_text)

            self.assertNotIn("张三", redacted_text)
            self.assertNotIn("45岁", redacted_text)
            self.assertNotIn("李医生", redacted_text)
            self.assertNotIn("某某医院检验科", redacted_text)

    def test_cli_redacts_pathology_report_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            input_dir = base / "input"
            output_dir = base / "output"
            input_dir.mkdir()

            source_pdf = input_dir / "pathology.pdf"
            create_extended_pdf(source_pdf)

            subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(input_dir), str(output_dir)],
                check=True,
                capture_output=True,
                text=True,
            )

            output_pdf = output_dir / "pathology_redacted.pdf"
            self.assertTrue(output_pdf.exists())

            doc = fitz.open(output_pdf)
            redacted_text = "\n".join(page.get_text() for page in doc)
            doc.close()
            redacted_text = unicodedata.normalize("NFKC", redacted_text)

            self.assertIn("姓名", redacted_text)
            self.assertIn("受检者", redacted_text)
            self.assertIn("条形码", redacted_text)
            self.assertIn("公司条码", redacted_text)
            self.assertIn("样本编号", redacted_text)
            self.assertIn("送检单位", redacted_text)
            self.assertIn("送检医生", redacted_text)
            self.assertIn("送检医院", redacted_text)
            self.assertIn("送检医师", redacted_text)
            self.assertIn("性别:男", redacted_text)
            self.assertIn("报告日期:2026-05-13", redacted_text)
            self.assertIn("科室/病区:外科", redacted_text)

            self.assertNotIn("张三", redacted_text)
            self.assertNotIn("李四", redacted_text)
            self.assertNotIn("BC-777", redacted_text)
            self.assertNotIn("COMP-888", redacted_text)
            self.assertNotIn("YP-123", redacted_text)
            self.assertNotIn("某某医院病理科", redacted_text)
            self.assertNotIn("王医生", redacted_text)
            self.assertNotIn("第一人民医院", redacted_text)
            self.assertNotIn("赵主任", redacted_text)

    def test_cli_respects_max_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            input_dir = base / "input"
            output_dir = base / "output"
            input_dir.mkdir()

            source_pdf = input_dir / "multi-page.pdf"
            create_multi_page_pdf(source_pdf)

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    str(input_dir),
                    str(output_dir),
                    "--max-pages",
                    "1",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output_pdf = output_dir / "multi-page_redacted.pdf"
            self.assertTrue(output_pdf.exists())

            doc = fitz.open(output_pdf)
            page_texts = [unicodedata.normalize("NFKC", page.get_text()) for page in doc]
            doc.close()

            self.assertNotIn("第一页患者", page_texts[0])
            self.assertIn("第二页患者", page_texts[1])


if __name__ == "__main__":
    unittest.main()
