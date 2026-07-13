# PDF 批量脱敏工具

这个脚本用于批量处理 PDF，把以下敏感信息从文档里直接擦除：

- 姓名 / 受检者
- 年龄
- 门诊/住院号 / 病历号 / 病案号
- 床号
- 条形码 / 样本编号
- 送检医生
- 送检单位 / 送检医院 / 送检科室

适用于英夫利昔单抗耐药检测（谷浓度、抗药抗体 ADA）等检验报告的批量脱敏。

它会保留字段标签本身，只删除字段值，例如把 `姓名：张三` 处理成 `姓名：`。

## 适用范围

- 适合文本型 PDF（能正常复制文字的 PDF）
- 不适合纯图片/扫描版 PDF；这类文件需要先做 OCR

## 安装

```bash
python3 -m pip install -r requirements.txt
```

## 用法

处理整个目录：

```bash
python3 redact_pdf_batch.py ./input_pdfs ./output_pdfs
```

递归处理子目录：

```bash
python3 redact_pdf_batch.py ./input_pdfs ./output_pdfs --recursive
```

输出黑色遮罩：

```bash
python3 redact_pdf_batch.py ./input_pdfs ./output_pdfs --fill-color black
```

处理单个文件：

```bash
python3 redact_pdf_batch.py ./report.pdf ./report_redacted.pdf
```

## 输出规则

- 目录模式下，输出文件名默认追加 `_redacted`
- 单文件模式下，可以直接指定输出 PDF 路径

## 脱敏逻辑

脚本会按页面逐行读取文字字符坐标，识别以下字段后，对字段值区域执行 PDF redaction：

- `姓名` / `受检者`
- `年龄`
- `门诊/住院号` / `病历号` / `病案号`
- `床号`
- `条形码` / `公司条码` / `样本编号`
- `送检医生` / `送检医师`
- `送检单位` / `送检医院` / `送检科室`

检测项目、谷浓度、抗药抗体结果、参考范围、检测方法等临床检验数据会保留。

## 测试

```bash
python3 -m unittest tests/test_redact_pdf_batch.py
```
