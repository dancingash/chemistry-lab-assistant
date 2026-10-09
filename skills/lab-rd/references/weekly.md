# Lab Weekly Report

Generate a weekly `.pptx` from local daily Word cards and shared project references.

## Root and Paths

Resolve data and program paths through the shared entrypoint configuration.

Use these local paths only:

- Daily report source: `{root}/report/YYYY-MM/日报_YYYY-MM-DD.docx`
- Metadata index: `{root}/report/index.json`; monthly tracker: `{root}/report/YYYY-MM/项目追踪表_YYYY年MM月.docx`
- Project references: `{root}/references/*.yaml`
- Weekly PPT output: `{root}/report/YYYY-MM/周报_YYYY年MM月_第X周.pptx`

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

## Required Supporting Skills

Use the Documents skill/plugin to read the daily report `.docx`. Use the Presentations skill/plugin to create, render, verify, and export the `.pptx`.

## Data Extraction

Extract all records in the requested week date range from the daily report. Group by project, then sort each project by date ascending.

For testing records, extract these metrics from `【配方与细节】` when present:

| 指标 | 常见来源 |
|---|---|
| 粒径 | 粒径测试结果 |
| BET比表面积 | BET / 氮气吸附测试结果 |
| 孔容 | 孔容数据 |
| 平均孔径 | 平均孔径数据 |
| 吸附率 | 吸附实验结果 |
| 官能团载量 | 滴定 / 元素分析结果 |
| 树脂颜色 | 外观描述 |
| 机械强度 | 球压测试结果 |
| 形貌 | 显微镜观察 |

Use active project reference files where `status: active`, excluding `project_template.yaml`.
Read each project's `targets` and `chart_groups`.
From a main reference's `effective_date`, group records whose original project ID is listed in
`legacy_project_ids` under that main project, keeping original project and sample IDs visible. Do not rewrite older reports. An inactive
reference is historical, not necessarily completed.

## PPT Structure

Create slides in this order:

1. Cover slide
2. Weekly experiment summary table for all projects
3. Stage map or project-level overview, when useful for the reporting period
4. One progress slide for each active project with records in the week

### Slide 1: Cover

Title:

```text
YYYY年MM月 第X周研发工作汇报
```

Include the reporting date range, active project count, experiment record count, and a concise thesis for the week. Do not include table-level details on the cover.

### Slide 2: Weekly Experiment Summary Table

Title:

```text
YYYY年MM月 第X周实验总结
```

Table columns:

| 项目 | 样品/编号 | 日期 | 实验类型/阶段 | 关键配方调整 | 关键结果 | 结论/后续 |
|---|---|---|---|---|---|---|

Use one row per experiment record or sample. Merge continuous records for the same sample on the same day when needed to fit the slide, but keep the sample traceable.

Derive `关键配方调整` from `【配方与细节】` and include only decision-relevant parameter changes, such as catalyst ratio, porogen system, crosslinking degree, PEG molecular weight, base/catalyst system, solvent system, reaction temperature, or key post-treatment change. Do not list the full recipe, full feed quantities, or step-by-step operation details.

Derive `关键结果` from testing, appearance, yield, mass change, BET, particle size, pore structure, residual chlorine, adsorption, loading, or qualitative observations. Derive `结论/后续` from `【今日实验】` and `【后续跟进】` in concise materials R&D language.

If the table has too many rows, keep the most decision-relevant records on Slide 2, compress text to short phrases, and expand details on project progress slides.

### Stage Map / Overview

Place this after the weekly experiment summary table. Use it only when it helps explain multi-week progression, route switching, or project prioritization.

### Project Progress Slides

Each active project slide contains:

- Title: `{project_id} {project_name} · 第X周进展`
- Left area: sample testing data table, only for samples with test data
- Right area: performance charts based on reference `chart_groups`
- Bottom area: `本周小结` and `下周计划`

Testing data table columns:

| 样品编号 | 粒径(mm) | BET(m²/g) | 孔容(mL/g) | 孔径(nm) | 吸附率(%) | 官能团载量(mmol/g) | 颜色 | 强度 | 形貌 |
|---|---|---|---|---|---|---|---|---|---|

For qualitative fields use `达标`, `未达标`, or `部分达标`, with short evidence where space allows.

## Chart Rules

- `chart_groups.radar`: create a radar chart with normalized values against target.
- `chart_groups.bar`: create bar charts with target lines.
- `chart_groups.qualitative`: list qualitative results as concise text below charts.
- A target marked `target_status: pending` has no numeric acceptance line or pass/fail judgment.
  Stage-specific targets apply only when the sample's level is explicitly identified;
  use that project's configured tolerance for that sample alone.
- For `min` targets, ratio is measured value divided by target value.
- For `range` targets, compare against the midpoint and show range boundaries.
- If there is no test data, replace the chart area with `本周暂无测试数据`.

## Summary and Plan Drafting

Generate project slide summary text in materials R&D language, plain and direct, within 100 Chinese characters where possible:

- `本周小结`: combine experiment conclusions and note target gaps when test data exists.
- `下周计划`: use the newest `【后续跟进】` per sample and list sample-specific next actions.

Show summaries and plans to the user for confirmation before finalizing the PPT.

## Workflow

1. Determine `YYYY-MM`, `YYYY年MM月`, and week number/date range from the user or current date.
2. Query the requested date range through `{program}/scripts/lab_records.py`; include both months for a cross-month week.
3. Read only project references corresponding to the returned records; respect active status.
4. Extract weekly records, key formulation adjustments, key results, and follow-up actions; group by project and sample.
5. Build the cover, Slide 2 weekly experiment summary table, optional stage map/overview, project progress slides, and charts.
6. Render/verify the PPT with the Presentations skill.
7. Save to `{root}/report/YYYY-MM/周报_YYYY年MM月_第X周.pptx`.
8. Report the output path and included projects.

## Constraints

- Do not read or write Google Drive by default.
- On Slide 2, include only key formulation adjustments that affect the experimental judgment; do not include full recipes, full feed quantities, or step-by-step operating details.
- Keep the weekly experiment summary table on Slide 2 immediately after the cover.
- Do not create project slides for inactive projects unless the user explicitly asks.
- Project YAML belongs in the data directory. Instruction references belong in this installed skill.
