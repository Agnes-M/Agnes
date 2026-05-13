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


if __name__ == "__main__":
    unittest.main()
