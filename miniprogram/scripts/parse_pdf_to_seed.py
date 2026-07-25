#!/usr/bin/env python3
"""从重大项目跟进表 PDF 解析 reps / hospitals 种子数据。"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    print('请先安装: pip install pymupdf', file=sys.stderr)
    sys.exit(1)

LEVELS = ['公立三级', '公立二级', '公立一级', '民营一级', '民营二级', '其它']
SYSTEMS = ['共建客户(专线)', '共建客户(混线)', '常规业务']
REGIONS = ('01杭州', '38瓯海')


def make_id(prefix: str, *parts: str) -> str:
    raw = '|'.join(str(p).strip() for p in parts if p)
    return f"{prefix}_{hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]}"


def extract_lines(pdf_path: Path) -> list[str]:
    doc = fitz.open(pdf_path)
    lines = []
    for page in doc:
        for line in page.get_text().splitlines():
            s = line.strip()
            if s:
                lines.append(s)
    return lines


def parse_records(lines: list[str]) -> list[dict]:
    records = []
    i = 0
    header_done = False

    while i < len(lines):
        line = lines[i]
        if line in ('区域', '经理', '主管', '代表', '医院名称', '医院等级', '业务体系'):
            header_done = True
            i += 1
            continue
        if line.startswith('项目名称') or line.startswith('目标销量'):
            break
        if line not in REGIONS:
            i += 1
            continue
        if i + 4 >= len(lines):
            break

        region = lines[i]
        manager = lines[i + 1]
        supervisor = lines[i + 2]
        rep_name = lines[i + 3]
        i += 4

        hospital_parts = []
        level = ''
        business = '常规业务'

        while i < len(lines):
            cur = lines[i]
            if cur in REGIONS:
                break
            if cur in LEVELS:
                level = cur
                i += 1
                if i < len(lines) and lines[i] in SYSTEMS:
                    business = lines[i]
                    i += 1
                break
            hospital_parts.append(cur)
            i += 1

        hospital_name = ''.join(hospital_parts).strip()
        if not hospital_name:
            continue
        if not level:
            level = '其它'

        records.append({
            'region': region,
            'manager': manager,
            'supervisor': supervisor,
            'rep_name': rep_name,
            'hospital_name': hospital_name,
            'level': level,
            'business_system': business,
        })

    return records


def build_seed(records: list[dict]) -> tuple[list[dict], list[dict]]:
    reps_map: dict[tuple, dict] = {}
    hospitals_seen: set[tuple] = set()
    hospitals: list[dict] = []

    for row in records:
        rep_key = (row['region'], row['manager'], row['supervisor'], row['rep_name'])
        if rep_key not in reps_map:
            rep_id = make_id('rep', *rep_key)
            reps_map[rep_key] = {
                '_id': rep_id,
                'name': row['rep_name'],
                'supervisor': row['supervisor'],
                'manager': row['manager'],
                'region': row['region'],
            }
        rep_id = reps_map[rep_key]['_id']
        hosp_key = (rep_id, row['hospital_name'])
        if hosp_key in hospitals_seen:
            continue
        hospitals_seen.add(hosp_key)
        hospitals.append({
            '_id': make_id('hosp', rep_id, row['hospital_name']),
            'repId': rep_id,
            'name': row['hospital_name'],
            'level': row['level'],
            'businessSystem': row['business_system'],
        })

    reps = sorted(reps_map.values(), key=lambda x: (x['region'], x['name']))
    hospitals.sort(key=lambda x: (x['repId'], x['name']))
    return reps, hospitals


def main():
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('uploads/台账.pdf')
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('miniprogram/seed-data')

    lines = extract_lines(pdf_path)
    records = parse_records(lines)
    reps, hospitals = build_seed(records)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'reps.json').write_text(json.dumps(reps, ensure_ascii=False, indent=2), encoding='utf-8')
    (out_dir / 'hospitals.json').write_text(json.dumps(hospitals, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'解析记录: {len(records)}')
    print(f'销售代表: {len(reps)}')
    print(f'医院: {len(hospitals)}')
    fufang = next((r for r in reps if r['name'] == '傅芳'), None)
    if fufang:
        count = sum(1 for h in hospitals if h['repId'] == fufang['_id'])
        print(f'傅芳名下医院: {count}')


if __name__ == '__main__':
    main()
