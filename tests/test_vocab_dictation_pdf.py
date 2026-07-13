from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

import fitz


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "vocab_dictation_pdf.py"
CHINESE_FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
ENGLISH_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9()]*\.?")


def create_vocab_sample_pdf(pdf_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_font(fontname="zh", fontfile=CHINESE_FONT)
    page.insert_text((72, 72), "1.personal", fontsize=12)
    page.insert_text((72, 96), "adj.私人的，个人的", fontname="zh", fontsize=12)
    page.insert_text((72, 120), "2.tie", fontsize=12)
    page.insert_text((72, 144), "v. 系；联系n. 联系", fontname="zh", fontsize=12)
    page.insert_text((72, 168), "高考英语核心高频688 个词汇", fontname="zh", fontsize=12)
    doc.save(pdf_path)
    doc.close()


class VocabDictationPdfTests(unittest.TestCase):
    def test_cli_removes_english_and_keeps_chinese(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            source_pdf = base / "vocab.pdf"
            output_pdf = base / "vocab_dictation.pdf"
            create_vocab_sample_pdf(source_pdf)

            subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(source_pdf), str(output_pdf)],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertTrue(output_pdf.exists())

            doc = fitz.open(output_pdf)
            redacted_text = unicodedata.normalize(
                "NFKC", "\n".join(page.get_text() for page in doc)
            )
            doc.close()

            self.assertIn("私人的", redacted_text)
            self.assertIn("个人的", redacted_text)
            self.assertIn("系", redacted_text)
            self.assertIn("联系", redacted_text)
            self.assertIn("高考英语核心高频688 个词汇", redacted_text)
            self.assertNotRegex(redacted_text, ENGLISH_TOKEN_PATTERN)
            self.assertNotIn("personal", redacted_text)
            self.assertNotIn("tie", redacted_text)


if __name__ == "__main__":
    unittest.main()
