import tempfile
import unittest
from pathlib import Path

import fitz

from redact_pdfs import process_paths


def create_sample_pdf(target: Path, patient_name: str) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), f"姓名：{patient_name}    性别：男    年龄：38岁")
    page.insert_text((72, 102), "送检医生：李主任")
    page.insert_text((72, 132), "送检单位：北京第一医院病理科")
    page.insert_text((72, 162), "标本类型：血液")
    document.save(target)
    document.close()


def extract_text(pdf_path: Path) -> str:
    document = fitz.open(pdf_path)
    text = "".join(page.get_text() for page in document)
    document.close()
    return text


class RedactPdfTests(unittest.TestCase):
    def test_redacts_sensitive_fields_in_single_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_pdf = temp_path / "sample.pdf"
            output_dir = temp_path / "output"
            create_sample_pdf(input_pdf, "张三")

            results = process_paths(input_pdf, output_dir)
            output_pdf = output_dir / "sample.pdf"
            text = extract_text(output_pdf)

            self.assertEqual(len(results), 1)
            self.assertTrue(output_pdf.exists())
            self.assertIn("姓名：", text)
            self.assertIn("年龄：", text)
            self.assertIn("送检医生：", text)
            self.assertIn("送检单位：", text)
            self.assertNotIn("张三", text)
            self.assertNotIn("38岁", text)
            self.assertNotIn("李主任", text)
            self.assertNotIn("北京第一医院病理科", text)
            self.assertIn("标本类型：血液", text)
            self.assertGreaterEqual(results[0].redaction_count, 4)

    def test_processes_pdf_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            output_dir = temp_path / "output"
            nested_dir = input_dir / "nested"
            nested_dir.mkdir(parents=True)
            create_sample_pdf(input_dir / "first.pdf", "王五")
            create_sample_pdf(nested_dir / "second.pdf", "赵六")

            results = process_paths(input_dir, output_dir)

            self.assertEqual(len(results), 2)
            self.assertTrue((output_dir / "first.pdf").exists())
            self.assertTrue((output_dir / "nested" / "second.pdf").exists())
            self.assertNotIn("王五", extract_text(output_dir / "first.pdf"))
            self.assertNotIn("赵六", extract_text(output_dir / "nested" / "second.pdf"))


if __name__ == "__main__":
    unittest.main()
