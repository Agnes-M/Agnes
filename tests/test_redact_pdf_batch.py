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


def run_redaction(input_dir: Path, output_dir: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(input_dir), str(output_dir), *extra_args],
        check=True,
        capture_output=True,
        text=True,
    )


def read_redacted_text(output_pdf: Path) -> str:
    doc = fitz.open(output_pdf)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return unicodedata.normalize("NFKC", text)


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

            result = run_redaction(input_dir, output_dir)

            output_pdf = output_dir / "report_redacted.pdf"
            self.assertTrue(output_pdf.exists(), result.stdout)
            redacted_text = read_redacted_text(output_pdf)

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

    def test_cli_redacts_infliximab_resistance_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            input_dir = base / "input"
            output_dir = base / "output"
            input_dir.mkdir()

            source_pdf = input_dir / "infliximab_report.pdf"
            create_pdf(
                source_pdf,
                [
                    [
                        "英夫利昔单抗耐药检测报告",
                        "姓名：王某某  性别：女  年龄：32岁  门诊/住院号：20240315001",
                        "送检医院：浙江大学医学院附属第一医院  科室/病区：消化内科",
                        "送检医生：张医生  送检单位：消化内科病区  样本编号：IFX-20240713-0088",
                        "临床诊断：克罗恩病  样本类型：血清",
                        "检测项目：英夫利昔单抗谷浓度、抗药抗体(ADA)",
                        "英夫利昔单抗谷浓度：2.5 μg/mL  参考范围：3-7 μg/mL",
                        "抗药抗体(ADA)：阳性  游离抗药抗体：阳性  总抗药抗体：阴性",
                        "检测方法：ELISA  采样日期：2024-07-10  报告日期：2024-07-13",
                        "报告编号：LAB-IFX-20240713-001",
                    ]
                ],
            )

            result = run_redaction(input_dir, output_dir)

            output_pdf = output_dir / "infliximab_report_redacted.pdf"
            self.assertTrue(output_pdf.exists(), result.stdout)
            redacted_text = read_redacted_text(output_pdf)

            self.assertIn("英夫利昔单抗耐药检测报告", redacted_text)
            self.assertIn("英夫利昔单抗谷浓度", redacted_text)
            self.assertIn("抗药抗体(ADA)", redacted_text)
            self.assertIn("游离抗药抗体", redacted_text)
            self.assertIn("总抗药抗体", redacted_text)
            self.assertIn("检测方法:ELISA", redacted_text)
            self.assertIn("参考范围:3-7", redacted_text)
            self.assertIn("临床诊断:克罗恩病", redacted_text)
            self.assertIn("报告编号:LAB-IFX-20240713-001", redacted_text)

            self.assertNotIn("王某某", redacted_text)
            self.assertNotIn("32岁", redacted_text)
            self.assertNotIn("20240315001", redacted_text)
            self.assertNotIn("浙江大学医学院附属第一医院", redacted_text)
            self.assertNotIn("消化内科病区", redacted_text)
            self.assertNotIn("张医生", redacted_text)
            self.assertNotIn("IFX-20240713-0088", redacted_text)

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

            run_redaction(input_dir, output_dir, "--max-pages", "1")

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
