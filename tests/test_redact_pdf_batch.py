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


def create_pdf(pdf_path: Path, pages: list[list[str]]) -> None:
    doc = fitz.open()
    for lines in pages:
        page = doc.new_page()
        page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
        for index, line in enumerate(lines):
            page.insert_text(
                (72, 96 + index * 30),
                line,
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
            create_pdf(
                source_pdf,
                [
                    [
                        "姓名：张三  性别：男  年龄：45岁  条形码：ABC-123",
                        "送检医生：李医生  送检单位：某某医院检验科  样本类型：组织",
                        "受检者：赵六  样本编号：SP-001",
                        "送检医院：协和医院  科室/病区：病理科",
                        "报告编号：RPT-001",
                    ]
                ],
            )

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
            self.assertIn("受检者", redacted_text)
            self.assertIn("样本编号", redacted_text)
            self.assertIn("送检医院", redacted_text)
            self.assertIn("性别:男", redacted_text)
            self.assertIn("报告编号:RPT-001", redacted_text)

            self.assertNotIn("张三", redacted_text)
            self.assertNotIn("45岁", redacted_text)
            self.assertNotIn("李医生", redacted_text)
            self.assertNotIn("某某医院检验科", redacted_text)
            self.assertNotIn("ABC-123", redacted_text)
            self.assertNotIn("赵六", redacted_text)
            self.assertNotIn("SP-001", redacted_text)
            self.assertNotIn("协和医院", redacted_text)

    def test_cli_honors_max_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            input_dir = base / "input"
            output_dir = base / "output"
            input_dir.mkdir()

            source_pdf = input_dir / "report.pdf"
            create_pdf(
                source_pdf,
                [
                    ["姓名：第一页患者  性别：男", "报告编号：PAGE-1"],
                    ["姓名：第二页患者  性别：女", "报告编号：PAGE-2"],
                ],
            )

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

            output_pdf = output_dir / "report_redacted.pdf"
            self.assertTrue(output_pdf.exists())

            doc = fitz.open(output_pdf)
            page_1_text = unicodedata.normalize("NFKC", doc[0].get_text())
            page_2_text = unicodedata.normalize("NFKC", doc[1].get_text())
            doc.close()

            self.assertNotIn("第一页患者", page_1_text)
            self.assertIn("第二页患者", page_2_text)
            self.assertIn("报告编号:PAGE-1", page_1_text)
            self.assertIn("报告编号:PAGE-2", page_2_text)


if __name__ == "__main__":
    unittest.main()
