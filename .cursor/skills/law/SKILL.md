---
name: law
description: Guides legal and privacy-compliant PDF redaction for medical and lab documents. Use when working on 脱敏, redaction, PII, 个人信息, 隐私合规, compliance, legal review, or extending redaction rules in this repository.
---

# Law — 文档脱敏合规

## 何时使用

在以下场景加载本 skill：

- 新增、修改或审查 PDF 脱敏规则
- 判断某字段是否属于应擦除的个人信息
- 评估脱敏方案是否符合隐私合规要求
- 处理医疗检验报告、病理报告等含敏感字段的文档

## 核心原则

1. **最小必要**：只擦除字段值，保留标签（如 `姓名：` 保留，`张三` 擦除）
2. **不可逆**：使用 PDF redaction（`add_redact_annot` + `apply_redactions`），不是简单覆盖文字
3. **可验证**：每次规则变更必须跑测试，并在样例 PDF 上人工抽查
4. **不误伤**：非敏感业务字段（报告编号、检测项目、诊断结论等）不得脱敏

## 当前脱敏范围

本仓库 `redact_pdf_batch.py` 默认擦除以下字段值：

| 字段 | 说明 |
|------|------|
| 姓名 / 患者姓名 | 个人身份标识 |
| 年龄 | 可识别个人的辅助信息 |
| 送检医生 / 送检医师 | 医务人员信息 |
| 送检单位 | 机构信息，可能间接识别个人 |

## 合规参考

处理中国公民个人信息时，注意：

- 《个人信息保护法》：脱敏属于降低个人信息风险的措施；处理目的应明确、范围应最小
- 医疗健康场景：姓名、年龄、送检信息通常属于个人信息或敏感个人信息关联信息
- 对外共享、科研归档、第三方交付前，应确认脱敏结果满足数据使用协议要求

详细检查项见 [compliance-checklist.md](compliance-checklist.md)。

## 扩展脱敏规则

### 决策流程

```
需要新增字段？
├─ 是否直接识别个人？ → 是 → 加入脱敏规则
├─ 是否与其他字段组合可识别个人？ → 是 → 评估后通常加入
├─ 是否为业务必需保留字段？ → 是 → 不脱敏
└─ 不确定 → 先询问用户或法务，不擅自脱敏
```

### 实现步骤

1. 在 `DEFAULT_RULES` 添加 `RedactionRule`，pattern 必须捕获 `label` 和 `value` 命名组
2. 复用 `FIELD_STOP_PATTERN` 防止跨字段误匹配
3. 在 `tests/test_redact_pdf_batch.py` 的样例 PDF 中加入该字段
4. 断言：标签保留、值消失、相邻非敏感字段不受影响
5. 运行：`python3 -m unittest tests/test_redact_pdf_batch.py`

### Pattern 约束

- 使用 `unicodedata.normalize("NFKC", ...)` 兼容全角/半角
- `value` 组不要贪婪跨越多个字段（用 `FIELD_STOP_PATTERN` 或精确边界）
- 标签别名写在 `label` 组内（如 `送检医生|送检医师`）

## 常见应脱敏字段（待用户确认后添加）

以下字段在医疗文档中常见，但**不在**当前默认规则中；仅在用户明确要求时扩展：

- 身份证号、手机号、住址
- 门诊号 / 住院号（可能关联个人）
- 条码下方的患者编号

## 不应脱敏的字段

- 报告编号、标本编号
- 检测项目名称与结果
- 诊断意见、病理描述（除非用户明确要求）
- 性别（当前测试用例保留；是否脱敏取决于业务要求）

## 质量检查清单

```
- [ ] 标签文字仍可见
- [ ] 字段值不可复制、不可搜索
- [ ] 相邻字段未被截断
- [ ] 单元测试通过
- [ ] 对真实样例 PDF 抽查至少 1 份
```

## 限制说明

- 仅适用于**文本型 PDF**；扫描件需 OCR 后再脱敏
- 本 skill 提供工程实践指导，不构成法律意见；具体合规结论需法务确认
