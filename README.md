# PDF 脱敏工具

这是一个用于批量脱敏 PDF 的命令行程序，默认会删除以下敏感信息：

- 姓名
- 年龄
- 送检医生
- 送检单位

程序会尽量保留字段标签本身，例如保留 `姓名：`，只覆盖后面的具体内容。

## 适用场景

- PDF 里包含可提取的文本内容
- 报告、送检单、病理单等结构化文档
- 需要批量处理整个目录中的 PDF 文件

## 限制说明

当前版本针对“文本型 PDF”工作良好。如果你的 PDF 是扫描图片，程序无法直接识别图片中的文字；这种情况需要先接入 OCR 流程。

## 安装

```bash
python3 -m pip install -r requirements.txt
```

## 用法

处理单个 PDF：

```bash
python3 redact_pdfs.py ./input/report.pdf ./output/report_redacted.pdf
```

处理整个目录：

```bash
python3 redact_pdfs.py ./input_pdfs ./output_pdfs
```

程序会递归处理目录下的所有 `.pdf` 文件，并在输出目录中保留相对目录结构。

## 示例输出

```text
[OK] /data/input/a.pdf -> /data/output/a.pdf (pages=2, redactions=4)
[OK] /data/input/b.pdf -> /data/output/b.pdf (pages=1, redactions=4)
共处理 2 个 PDF，3 页，执行 8 处脱敏。
```
