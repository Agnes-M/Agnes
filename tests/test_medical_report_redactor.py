from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

import fitz


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "medical_report_redactor.py"
CHINESE_FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"

OLD_TEXT_PATTERNS = [
    r"(姓\s*名[:：]?\s*)(.*?)(?=\s+性\s*别|性别|门诊/住院号|条形码|报告编号|公司条码|$)",
    r"(送检单位[:：]\s*)(.*?)(?=\s+送检医生|送检医师|送检科室|样本类型|临床诊断|备注|检验者|审核者|批准人|$)",
    r"(送检医生[:：]\s*)(.*?)(?=\s+其他信息|联系电话|采集时间|样本类型|临床诊断|$)",
]


def create_problematic_pdf(pdf_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
    page.insert_text(
        (72, 96),
        "姓名：欧阳　娜娜  性别：女  条形码：ZX-9-77",
        fontname="zh",
        fontsize=14,
    )
    page.insert_text((72, 126), "送检医生：华", fontname="zh", fontsize=14)
    page.insert_text((72, 146), "佗", fontname="zh", fontsize=14)
    page.insert_text((72, 176), "送检单位：星海医院检验科", fontname="zh", fontsize=14)
    doc.save(pdf_path)
    doc.close()


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def old_matches(page: fitz.Page) -> list[str]:
    text = page.get_text("text", flags=0)
    values: list[str] = []
    for pattern in OLD_TEXT_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.S):
            values.append(match.group(2).replace("\n", " ").strip())
    return values


class MedicalReportRedactorTests(unittest.TestCase):
    def test_old_search_for_chain_fails_but_new_script_redacts_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            input_dir = base / "input"
            output_dir = base / "output"
            input_dir.mkdir()

            source_pdf = input_dir / "report.pdf"
            create_problematic_pdf(source_pdf)

            doc = fitz.open(source_pdf)
            page = doc[0]
            extracted_values = old_matches(page)
            doc.close()

            self.assertIn("欧阳 娜娜", [normalize_text(item) for item in extracted_values])
            self.assertTrue(any("送检单位" in normalize_text(item) for item in extracted_values))

            doc = fitz.open(source_pdf)
            page = doc[0]
            self.assertEqual(page.search_for("欧阳 娜娜"), [])
            doc.close()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    str(input_dir),
                    str(output_dir),
                    "--max-pages",
                    "3",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output_pdf = output_dir / "report_脱敏.pdf"
            self.assertTrue(output_pdf.exists(), result.stdout)

            doc = fitz.open(output_pdf)
            redacted_text = normalize_text("\n".join(page.get_text() for page in doc))
            doc.close()

            self.assertIn("姓名", redacted_text)
            self.assertIn("送检医生", redacted_text)
            self.assertIn("送检单位", redacted_text)
            self.assertIn("条形码", redacted_text)

            self.assertNotIn("欧阳", redacted_text)
            self.assertNotIn("娜娜", redacted_text)
            self.assertNotIn("华", redacted_text)
            self.assertNotIn("佗", redacted_text)
            self.assertNotIn("星海医院检验科", redacted_text)
            self.assertNotIn("ZX-9-77", redacted_text)


if __name__ == "__main__":
    unittest.main()
