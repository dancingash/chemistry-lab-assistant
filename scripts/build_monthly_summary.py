from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import yaml


WEEK_LABELS = ["第一周", "第二周", "第三周", "第四周", "第五周", "第六周"]


def week_label(number):
    return WEEK_LABELS[number - 1] if number <= len(WEEK_LABELS) else f"第{number}周"


def infer_weeks(dates: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    previous: dt.date | None = None
    for date_text in sorted(dates):
        date = dt.date.fromisoformat(date_text)
        if previous is not None and (date - previous).days >= 2:
            groups.append(current)
            current = []
        current.append(date_text)
        previous = date
    if current:
        groups.append(current)
    return groups


def read_project_reference(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    return {
        "project_id": data.get("project_id", path.stem),
        "project_name": data.get("project_name", path.stem),
        "targets": data.get("targets", {}),
        "effective_date": str(data.get("effective_date") or ""),
        "legacy_project_ids": data.get("legacy_project_ids", []),
    }


def format_targets(reference: dict) -> str:
    parts: list[str] = []
    for name, target in reference["targets"].items():
        if str(target.get("required", "")).lower() != "true":
            continue
        if target.get("target_status") == "pending":
            parts.append(f"{name}：数值目标待确定")
            continue
        target_type = target.get("type", "")
        unit = target.get("unit", "")
        suffix = f" {unit}" if unit else ""
        if target_type == "range":
            parts.append(f"{name}：{target.get('min')}~{target.get('max')}{suffix}")
        elif target_type == "min":
            parts.append(f"{name}：≥{target.get('value')}{suffix}")
        elif target_type == "max":
            parts.append(f"{name}：≤{target.get('value')}{suffix}")
        elif target_type == "qualitative":
            parts.append(f"{name}：{target.get('requirement')}")
    return "；\n".join(parts)


def canonical_project_ids(record: dict, references: dict[str, dict]) -> list[str]:
    """Group legacy IDs from the main context's effective date without editing records."""
    resolved: list[str] = []
    record_date = record.get("date", "")
    for raw_id in detect_project_ids([record]):
        project_id = raw_id
        for reference in references.values():
            if (raw_id in reference["legacy_project_ids"]
                    and reference["effective_date"]
                    and record_date >= reference["effective_date"]):
                project_id = reference["project_id"]
                break
        if project_id not in resolved:
            resolved.append(project_id)
    return resolved


def detect_project_ids(records: list[dict]) -> list[str]:
    ids: list[str] = []
    for record in records:
        for source in (record.get("project", ""), record.get("sample_id", "")):
            match = re.match(r"([A-Za-z][A-Za-z0-9_]*)(?=\s|-[0-9]{8}-|$)", source.strip())
            if match and match.group(1) not in ids:
                ids.append(match.group(1))
    return ids


def fallback_content(records: list[dict]) -> str:
    lines: list[str] = []
    for record in sorted(records, key=lambda item: (item["date"], item["sample_id"], item["experiment_type"])):
        date_label = record["date"][5:]
        summary = " ".join(record.get("today", "").split())
        details = "；".join(line.strip() for line in record.get("details", record.get("fields", {}).get("配方与细节", "")).splitlines())
        step = ' / ' + record['step'] if record.get('step') else ''
        line = f"{date_label} {record['experiment_type']}（{record['sample_id']}{step}）：{summary}"
        if details:
            line += f"；{details}"
        lines.append(line)
    return "\n".join(lines) if lines else "本周无该项目相关实验记录。"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("extract_json", type=Path)
    parser.add_argument("--references-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--month", required=True, help="YYYY-MM")
    parser.add_argument("--use-legacy-june-copy", action="store_true", help="Compatibility option: requires an explicit local --legacy-copy-file")
    parser.add_argument("--legacy-copy-file", type=Path, help="Local historical archive; never a default source")
    args = parser.parse_args()

    source = json.loads(args.extract_json.read_text(encoding="utf-8"))
    records = [record for record in source["records"] if record.get("date", "").startswith(args.month)]
    if not records:
        raise SystemExit(f"No records found for {args.month}")

    weeks = infer_weeks(sorted({record["date"] for record in records}))
    archive = None
    if args.use_legacy_june_copy:
        if not args.legacy_copy_file:
            parser.error("Historical reproduction requires --legacy-copy-file")
        archive = json.loads(args.legacy_copy_file.read_text(encoding="utf-8"))
        if archive.get("month") != args.month:
            parser.error("Historical archive month does not match --month")
        if archive.get("week_ranges"):
            weeks = archive["week_ranges"]
    week_by_date = {date: index + 1 for index, dates in enumerate(weeks) for date in dates}

    available_references = {
        reference["project_id"]: reference
        for path in args.references_dir.glob("*.yaml")
        if path.name != "project_template.yaml"
        for reference in [read_project_reference(path)]
    }
    projects_by_record = [canonical_project_ids(record, available_references) for record in records]
    project_ids = list(dict.fromkeys(project_id for ids in projects_by_record for project_id in ids))
    references = [available_references[project_id] for project_id in project_ids if project_id in available_references]
    if not references:
        raise SystemExit("No matching project references found")

    rows = []
    for reference in references:
        project_id = reference["project_id"]
        project_name = f"{project_id} {reference['project_name']}"
        target = format_targets(reference)
        project_records = [record for record, ids in zip(records, projects_by_record) if project_id in ids]
        for week_index, dates in enumerate(weeks, 1):
            week_records = [record for record in project_records if week_by_date[record["date"]] == week_index]
            content = fallback_content(week_records)
            follow_up = "；".join(record.get("follow_up", "") for record in week_records if record.get("follow_up"))
            comment = (follow_up[:118].rstrip("，；。 ") + "。") if follow_up else "后续安排待补。"
            if archive:
                entry = archive.get("projects", {}).get(project_id, {}).get(str(week_index), {})
                content = entry.get("content", content)
                comment = entry.get("comment", comment)
            rows.append(
                {
                    "week": week_label(week_index),
                    "project": project_name,
                    "target": target,
                    "content": content,
                    "comment": comment,
                }
            )

    year, month = args.month.split("-")
    output = {
        "month": args.month,
        "title": f"新品月度研发工作总结（{year}年{month}月）",
        "sheet_name": f"{year}.{month}",
        "week_ranges": [
            {
                "label": week_label(index + 1),
                "start": dates[0],
                "end": dates[-1],
                "dates": dates,
            }
            for index, dates in enumerate(weeks)
        ],
        "rows": rows,
        "included_projects": [f"{ref['project_id']} {ref['project_name']}" for ref in references],
        "source": source.get("source") or {"kind": "indexed_query", "read_log": source.get("read_log", [])},
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"rows={len(rows)}")
    for week in output["week_ranges"]:
        print(f"{week['label']}: {week['start']}~{week['end']}")


if __name__ == "__main__":
    main()
