# Lab Monthly Report

Fill the monthly R&D summary `.xlsx` template from local daily reports and shared project references.

## Root and Paths

Resolve data and program paths through the shared entrypoint configuration.

Use these local paths only:

- Daily report source: `{root}/report/YYYY-MM/日报_YYYY-MM-DD.docx`
- Metadata index: `{root}/report/index.json`; monthly tracker: `{root}/report/YYYY-MM/项目追踪表_YYYY年MM月.docx`
- Project references: `{root}/references/*.yaml`
- XLSX template: `{program}/templates/monthly-summary.xlsx`
- Monthly XLSX output: `{root}/report/YYYY-MM/新品月度研发工作总结_YYYY年MM月.xlsx`

Create the month folder if it does not exist. Do not use Google Drive paths.

## Indexed record access

Use the installed virtual-environment Python to run `{program}/scripts/lab_records.py --root "{root}" query
--start YYYY-MM-DD --end YYYY-MM-DD --out OUTPUT.json`. This refreshes changed source
metadata and returns matching `records` plus `read_log`. Load that output, not all monthly Word
files. Preserve sample, branch, step and record IDs. Deduplicate by record ID; conflicting
content must be resolved, not silently collapsed. Group tests by sample AND tested step.

If the period predates daily cards, follow [daily module](daily.md) historical lookup: list files only in
relevant months, resolve competing versions, and explicitly register one authoritative legacy
source per month with `refresh --legacy RELATIVE_PATH`. Never merge all updated snapshots.
Do not interpret an empty index result as proof that no historical work occurred.

Shared backgrounds are maintained by [context module](context.md). Read
`{program}/scripts/research_workflow_contract.md` for route/plan status and material quantities. Use
confirmed saved context; candidates under `work/` and adaptations are not official routes or evidence
of execution. Best selection does not prove passing tests. Match sample/branch/step and keep measured,
calculated and planned values distinct. Use the background version cited
by a record when interpreting historical conclusions. State explicitly when comparing historical
measurements against current targets; never rewrite the earlier conclusion. Standard reference
conditions are not actual-run data. Do not use hard-coded monthly example content in
`build_monthly_summary.py` for a new reporting period.
From a main reference's `effective_date`, group records whose original project ID is listed in
`legacy_project_ids` under the main project; keep original sample IDs and historical conclusions. Apply only mappings explicitly configured for this project.

## Required Supporting Skills

Use the Documents skill/plugin to read the daily report `.docx`. Use the Spreadsheets skill/plugin to copy, fill, render, verify, and save the `.xlsx` output.

## Template Shape

Use sheet name `YYYY.MM`.

Expected columns:

| 周次 | 项目名称 | 项目目标 | 研发内容（含配方细节/现象/数据） | 小结点评 |
|---|---|---|---|---|

Each project occupies weekly rows. If there are multiple active projects, append project blocks vertically and leave one blank row between project blocks when the template allows.

## Week Inference

Infer work weeks from dates that actually appear in the daily report. Do not hard-cut by calendar weeks.

Rules:

1. Sort all recorded work dates in the month ascending.
2. Start a new week when the gap between recorded dates is at least 2 days.
3. Label groups as `第一周`, `第二周`, `第三周`, `第四周`, etc.
4. A week with one recorded day is still a valid week.
5. If the month has fewer than four inferred weeks, leave remaining rows blank.

Show inferred week ranges to the user and ask for confirmation or adjustment before filling the spreadsheet.

## Field Generation

### 项目名称

Use:

```text
{project_id} {project_name}
```

### 项目目标

Read `targets` from the project reference and include all `required: true` metrics. Format by target type:

- `range`: `{指标}：{min}~{max} {unit}`
- `min`: `{指标}：≥{value} {unit}`
- `max`: `{指标}：≤{value} {unit}`
- `qualitative`: `{指标}：{requirement}`
- `target_status: pending`: `{指标}：数值目标待确定`，不作达标判断。

Stage-specific targets and tolerances come from the project's confirmed YAML.
Compare a sample only with its explicitly assigned level; never invent a default threshold.

This field is the same for all weeks of the same project.

### 研发内容

For each project and inferred week, summarize records by date ascending. Preserve formula details, observed phenomena, and test data exactly when available.

Use this style:

```text
04-08 合成：
以苯乙烯（15.32 g）、DVB（4.21 g）、BPO（0.18 g）为原料，70℃悬浮聚合8h，成球良好。

04-09 后处理：
氯甲基化：氯甲醚（12.5 mL）、ZnCl₂（0.5 g），40℃反应6h，产物呈淡黄色。
```

If the project has no records in a week, write `本周无该项目相关实验记录`.

### 小结点评

Write 80-120 Chinese characters:

- Combine the week's `【后续跟进】` content.
- If test data exists, compare it with reference targets and state gaps directly.
- End with a clear next action.

## Workflow

1. Determine target month from user or current date.
2. Query the entire target month through `{program}/scripts/lab_records.py`.
3. Read only project references corresponding to the returned records.
4. Infer work weeks and show ranges for confirmation.
5. Copy the template from `{program}/templates/monthly-summary.xlsx`.
6. Rename the sheet to `YYYY.MM`.
7. Fill project weekly rows.
8. Show cell drafts for user confirmation, especially `小结点评`.
9. Render/verify the spreadsheet.
10. Save to `{root}/report/YYYY-MM/新品月度研发工作总结_YYYY年MM月.xlsx`.
11. Report the output path and included projects.

## Constraints

- Do not read or write Google Drive by default.
- Preserve recipe data in `研发内容`; do not invent missing values.
- Keep comments plain, specific, and technical.
- Project YAML belongs in the data directory. Instruction references belong in this installed skill.
