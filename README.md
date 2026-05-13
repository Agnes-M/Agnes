# PDF 批量脱敏工具

这个脚本用于批量处理 PDF，把以下敏感信息从文档里直接擦除：

- 姓名
- 受检者
- 年龄
- 条形码
- 公司条码
- 样本编号
- 送检医生
- 送检医师
- 送检单位
- 送检医院

它会保留字段标签本身，只删除字段值，例如把 `姓名：张三` 处理成 `姓名：`。
另外，如果每页左上角页眉里重复出现患者姓名或报告编号，也会一并去掉。

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

只处理每个 PDF 的前 3 页：

```bash
python3 redact_pdf_batch.py ./input_pdfs ./output_pdfs --max-pages 3
```

## 输出规则

- 目录模式下，输出文件名默认追加 `_redacted`
- 单文件模式下，可以直接指定输出 PDF 路径

## 脱敏逻辑

脚本会按页面逐行读取文字字符坐标，识别以下字段后，对字段值区域执行 PDF redaction：

- `姓名`
- `受检者`
- `年龄`
- `条形码`
- `公司条码`
- `样本编号`
- `送检医生` / `送检医师`
- `送检单位` / `送检医院`

相比“先 `get_text()` 提值、再 `search_for()` 回找坐标”的做法，这种字符级定位方式对 PDF 中的换行、空格和兼容字形更稳。
脚本还会额外扫描每页左上角页眉区域，把重复出现的患者姓名和报告编号去掉，但不会把正文里的 `检测结果` 一起遮掉。

## 测试

```bash
python3 -m unittest tests/test_redact_pdf_batch.py
```
