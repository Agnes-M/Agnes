#!/usr/bin/env python3
"""
将 seed-data/*.json 通过云开发 HTTP API 或云函数批量导入数据库。

本脚本生成可在微信开发者工具「云开发控制台」或小程序内调用的导入指令。

推荐导入方式（微信开发者工具）:
  1. 打开云开发控制台 → 数据库
  2. 分别创建集合 reps、hospitals、projects
  3. 使用「导入」功能上传对应的 JSON 文件

或通过云函数 importSeedData 批量导入:
  在微信开发者工具 → 云函数 → importSeedData → 云端测试，传入:
  { "collection": "reps", "records": [...] }

本脚本辅助将大 JSON 文件拆分为云函数可接受的批次调用脚本。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def split_batches(records: list, batch_size: int = 20) -> list[list]:
    return [records[i : i + batch_size] for i in range(0, len(records), batch_size)]


def main():
    parser = argparse.ArgumentParser(description="生成云函数批量导入调用脚本")
    parser.add_argument("--seed-dir", type=Path, default=Path("seed-data"))
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("seed-data/import_calls.json"))
    args = parser.parse_args()

    calls = []
    for collection in ["reps", "hospitals", "projects"]:
        path = args.seed_dir / f"{collection}.json"
        if not path.exists():
            print(f"跳过（文件不存在）: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            records = json.load(f)
        for batch in split_batches(records, args.batch_size):
            calls.append({"collection": collection, "records": batch})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(calls, f, ensure_ascii=False, indent=2)

    print(f"已生成 {len(calls)} 个导入批次 → {args.output}")
    print("在微信开发者工具云函数 importSeedData 云端测试中，逐个粘贴 calls 数组元素执行。")


if __name__ == "__main__":
    main()
