from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

from vocab_dictation_sheet import extract_lines, parse_entries


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "vocab_dictation_sheet.py"
SOURCE_PDF = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/________688____1__c33e.pdf"
)
CHINESE_FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"


class VocabDictationSheetTests(unittest.TestCase):
    @unittest.skipUnless(SOURCE_PDF.exists(), "source vocabulary PDF is unavailable")
    def test_parse_all_688_entries(self) -> None:
        entries = parse_entries(extract_lines(SOURCE_PDF))
        numbers = {entry.number for entry in entries}
        self.assertEqual(len(entries), 688)
        self.assertEqual(numbers, set(range(1, 689)))

    @unittest.skipUnless(SOURCE_PDF.exists(), "source vocabulary PDF is unavailable")
    def test_generated_pdf_has_dictation_lines_and_chinese(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_pdf = Path(tmpdir) / "sheet.pdf"
            subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(SOURCE_PDF), str(output_pdf)],
                check=True,
                capture_output=True,
                text=True,
            )

            doc = fitz.open(output_pdf)
            text = "\n".join(page.get_text() for page in doc)
            page_count = doc.page_count
            doc.close()

            self.assertGreaterEqual(page_count, 10)
            self.assertIn("默写练习", text)
            self.assertIn("私人的，个人的", text)
            self.assertIn("英文", text)
            self.assertNotIn("personal", text.lower())

    def test_parse_mini_sample_lines(self) -> None:
        entries = parse_entries(
            [
                "1.personal",
                "adj.私人的，个人的",
                "262. adolescent",
                "adj.青春期的n.青少年",
                "656.democratic adj.民主的",
                "668.time-consuming",
                "adj.耗费时间的",
            ]
        )
        by_number = {entry.number: entry for entry in entries}
        self.assertEqual(by_number[1].english, "personal")
        self.assertEqual(by_number[1].chinese, "私人的，个人的")
        self.assertEqual(by_number[262].english, "adolescent")
        self.assertEqual(by_number[656].chinese, "民主的")
        self.assertEqual(by_number[668].english, "time-consuming")


if __name__ == "__main__":
    unittest.main()
