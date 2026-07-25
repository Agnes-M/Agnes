#!/usr/bin/env python3
"""
将 Excel 台账（重大项目跟进表）转换为云开发种子数据 JSON。

用法:
  python3 scripts/excel_to_seed.py 重大项目跟进表.xlsx
  python3 scripts/excel_to_seed.py 重大项目跟进表.xlsx --output-dir seed-data

输出:
  seed-data/reps.json
  seed-data/hospitals.json
  seed-data/projects.json

Excel 列名映射（请根据实际表头调整 COLUMN_MAP）:
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("请先安装依赖: pip install openpyxl", file=sys.stderr)
    sys.exit(1)


# 根据实际 Excel 表头调整此映射
COLUMN_MAP = {
    "region": ["区域", "大区"],
    "manager": ["经理", "区域经理"],
    "supervisor": ["主管", "销售主管"],
    "rep_name": ["代表", "销售代表", "代表姓名"],
    "hospital_name": ["医院", "医院名称", "客户名称"],
    "hospital_level": ["医院等级", "等级", "医院级别"],
    "business_system": ["业务体系", "业务类型"],
    "project_name": ["项目", "项目名称", "检验项目"],
    "bidding_info": ["标段信息", "标段"],
    "discount": ["折扣", "折扣（%）", "折扣%"],
    "add_difficulty": ["加项难度"],
    "status": ["当前状态", "状态", "项目状态"],
    "current_monthly_volume": ["当前月均销量", "月均销量", "当前销量"],
    "target_monthly_volume": ["目标销量", "目标销量/月", "目标月均销量"],
    "key_departments": ["重点科室", "关键人物", "重点科室/关键人物"],
    "action_plan": ["具体行动计划", "行动计划"],
    "weekly_progress": ["本周进展", "本周进度"],
    "next_week_plan": ["下周计划"],
    "blocker": ["卡点", "当前卡点"],
    "bronchoscopy_cases": ["本周气管镜例数", "气管镜例数"],
    "bronchoalveolar_lavage": ["本周肺泡灌洗液送检量", "肺泡灌洗液送检量"],
    "remark": ["备注"],
    "market_remark": ["市场部备注", "市场备注"],
}

VALID_STATUSES = {"加项入院", "已入院-上量", "未入院-上量", "非重点跟进"}


def make_id(prefix: str, *parts: str) -> str:
    raw = "|".join(str(p).strip() for p in parts if p)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def find_column_index(headers: list, candidates: list[str]) -> int | None:
    normalized = {str(h).strip(): i for i, h in enumerate(headers) if h}
    for name in candidates:
        if name in normalized:
            return normalized[name]
    for name in candidates:
        for header, idx in normalized.items():
            if name in header or header in name:
                return idx
    return None


def build_column_indices(headers: list) -> dict[str, int | None]:
    return {key: find_column_index(headers, names) for key, names in COLUMN_MAP.items()}


def cell_value(row: tuple, idx: int | None):
    if idx is None or idx >= len(row):
        return None
    val = row[idx]
    if val is None:
        return None
    if isinstance(val, str):
        return val.strip()
    return val


def parse_number(val) -> float:
    if val is None or val == "":
        return 0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else 0


def parse_key_departments(val) -> list[str]:
    if not val:
        return ["", ""]
    if isinstance(val, str):
        parts = re.split(r"[,，;；/、\n]", val)
        parts = [p.strip() for p in parts if p.strip()]
        return (parts + ["", ""])[:2]
    return ["", ""]


def normalize_status(val: str | None) -> str:
    if not val:
        return ""
    val = str(val).strip()
    return val if val in VALID_STATUSES else ""


def convert_excel(excel_path: Path, output_dir: Path) -> None:
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise ValueError("Excel 至少需要表头行和一行数据")

    headers = [str(h).strip() if h else "" for h in rows[0]]
    col = build_column_indices(headers)

    missing = [k for k in ("rep_name", "hospital_name", "project_name") if col[k] is None]
    if missing:
        raise ValueError(
            f"缺少必要列: {missing}。当前表头: {headers}。"
            f"请修改 scripts/excel_to_seed.py 中的 COLUMN_MAP。"
        )

    reps_map: dict[str, dict] = {}
    hospitals_map: dict[str, dict] = {}
    projects: list[dict] = []

    for row in rows[1:]:
        rep_name = cell_value(row, col["rep_name"])
        hospital_name = cell_value(row, col["hospital_name"])
        project_name = cell_value(row, col["project_name"])

        if not rep_name or not hospital_name or not project_name:
            continue

        region = cell_value(row, col["region"]) or ""
        manager = cell_value(row, col["manager"]) or ""
        supervisor = cell_value(row, col["supervisor"]) or ""

        rep_id = make_id("rep", region, manager, supervisor, rep_name)
        if rep_id not in reps_map:
            reps_map[rep_id] = {
                "_id": rep_id,
                "name": str(rep_name),
                "supervisor": str(supervisor),
                "manager": str(manager),
                "region": str(region),
            }

        hospital_id = make_id("hosp", rep_id, hospital_name)
        if hospital_id not in hospitals_map:
            hospitals_map[hospital_id] = {
                "_id": hospital_id,
                "repId": rep_id,
                "name": str(hospital_name),
                "level": str(cell_value(row, col["hospital_level"]) or "其它"),
                "businessSystem": str(cell_value(row, col["business_system"]) or "常规业务"),
            }

        key_depts = parse_key_departments(cell_value(row, col["key_departments"]))
        project_id = make_id("proj", hospital_id, project_name, cell_value(row, col["bidding_info"]) or "")

        projects.append({
            "_id": project_id,
            "hospitalId": hospital_id,
            "name": str(project_name),
            "biddingInfo": str(cell_value(row, col["bidding_info"]) or ""),
            "discount": str(cell_value(row, col["discount"]) or ""),
            "addDifficulty": str(cell_value(row, col["add_difficulty"]) or ""),
            "status": normalize_status(cell_value(row, col["status"])),
            "currentMonthlyVolume": parse_number(cell_value(row, col["current_monthly_volume"])),
            "targetMonthlyVolume": parse_number(cell_value(row, col["target_monthly_volume"])),
            "keyDepartments": [d for d in key_depts if d],
            "actionPlan": str(cell_value(row, col["action_plan"]) or ""),
            "weeklyProgress": str(cell_value(row, col["weekly_progress"]) or ""),
            "nextWeekPlan": str(cell_value(row, col["next_week_plan"]) or ""),
            "blocker": str(cell_value(row, col["blocker"]) or ""),
            "bronchoscopyCases": int(parse_number(cell_value(row, col["bronchoscopy_cases"]))),
            "bronchoalveolarLavage": int(parse_number(cell_value(row, col["bronchoalveolar_lavage"]))),
            "remark": str(cell_value(row, col["remark"]) or ""),
            "marketRemark": str(cell_value(row, col["market_remark"]) or ""),
            "updatedBy": str(rep_name),
        })

    output_dir.mkdir(parents=True, exist_ok=True)

    reps = list(reps_map.values())
    hospitals = list(hospitals_map.values())

    for name, data in [("reps", reps), ("hospitals", hospitals), ("projects", projects)]:
        path = output_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已生成 {path}（{len(data)} 条）")


def main():
    parser = argparse.ArgumentParser(description="Excel 台账转云开发种子数据")
    parser.add_argument("excel", type=Path, help="Excel 文件路径")
    parser.add_argument("--output-dir", type=Path, default=Path("seed-data"), help="输出目录")
    args = parser.parse_args()

    if not args.excel.exists():
        print(f"文件不存在: {args.excel}", file=sys.stderr)
        sys.exit(1)

    convert_excel(args.excel, args.output_dir)
    print("转换完成。")


if __name__ == "__main__":
    main()
