# Lab Daily Report

For completion of a calculated recipe batch, use [formulations](formulations.md) to recover its
revision and selected groups, then the completion tool. Batch fields 配方批次、配方批次版本、配方实验组
are retained with the plan reference. A completion report does not turn planned quantities into readings.

## Storage and tools

Resolve `{root}` (data) and `{program}` (installed package) through the entrypoint configuration.
Use local files; project background is shared with weekly/monthly reports outside skill folders.

- Daily facts: `{root}/report/YYYY-MM/日报_YYYY-MM-DD.docx`, one file per day.
- Monthly tracker: `{root}/report/YYYY-MM/项目追踪表_YYYY年MM月.docx`.
- Rebuildable metadata index: `{root}/report/index.json`.
- Project background: `{root}/references/{project_id}.yaml`.

Use Documents for Word editing and render verification. Run Python tools with the installed
virtual environment. Tool: `{program}/scripts/lab_records.py --help` (requires python-docx).
Read `{program}/scripts/lab_records_contract.md` when preparing saves or repairing sources/indexes.
Read `{program}/scripts/research_workflow_contract.md` for material tables, sample conversions,
literature proposals and missing-route communication.

## Targeted reading

1. Identify project, date, sample and operation. “Yesterday's sample” is not unique if several exist.
2. Run `lab_records.py --root "{root}" query --sample SAMPLE [--step S01] [--kind 合成]`.
   Period queries use `--start YYYY-MM-DD --end YYYY-MM-DD`. The tool checks changed files,
   refreshes metadata, and returns matching records plus a read log. Consult matching tracker rows.
3. Read only the matching project YAML and historical records relevant to the operation. Follow
   source sample/step only when provenance is needed. Tests remain attached to the tested step.
4. If history is absent, list filenames in the relevant month. Select the authoritative legacy Word
   using evidence; conflicting snapshots or ambiguous identities require one consolidated question.
   Register it with `refresh --legacy RELATIVE_PATH`. Never import every old snapshot or choose
   by filename/mtime alone. No match does not prove a sample never existed.

For a new experiment date found only inside a legacy monthly Word, create that day's card with
`migrate-day --date YYYY-MM-DD --legacy RELATIVE_PATH` after registering the source. This copies
all that day's records verbatim, adds stable record and origin IDs, and excludes their originals
from indexed summaries. Do not continue appending to the monthly Word. If a sample's ID is missing,
the descriptive label remains in the card; it has no tracker row until its identity is confirmed.

The index contains metadata/locations, not the sole copy of facts. Cold rebuilds may parse daily
Word locally; do not load all text into model context. Manual tracker changes that conflict with daily
facts require reconciliation. Do not silently overwrite unknown manual content in daily Word.

## Sample identity

- Main ID: `{project_id}-{first_synthesis_YYYYMMDD}-{sequence}`; numeric sequence starts at 1
  per project/date. Check existing IDs before allocation. Keep it through reactions and months.
- Steps: `S01`, `S02`, etc. for distinct reaction steps. Continuing, washing or drying the same
  step does not increment it. Tests explicitly identify the sample/branch and tested step.
- Independently treated portions append `-B01`, `-B02`, etc., retaining source sample and source
  step. Branch creation date is the split date. Further splitting can append another branch suffix.
  Independent repeat feed batches get new main IDs.
- Each record has its own stable `record_id` (UUID recommended). Reuse it for corrections/retries;
  use separate records per sample, including parallel batches. Preserve IDs on historical imports.
- Preserve historical sample IDs; never invent parentage or resolve “unknown prior sample” by guess.
  Unidentified but otherwise clear work still belongs in the daily card as `身份待确认`; retain its
  original sample description and link it to a numbered sample only after confirmation.

## Card format and easy input

Keep visible labels: `【记录标识】【项目】【样品编号】【创建日期】【步骤】【来源样品】`
`【来源步骤】【实验类型】【当前状态】【今日实验】【配方与细节】【后续跟进】`
and optional `【问题与风险】【背景版本】`, preceded by date and weekday.
When a plan is used, also keep `【方案工序】【方案编号】【方案版本】` with its exact numeric version.

Types: `合成`, `后处理`, `测试`; specify operation names in today's experiment. States:
`合成中`, `待后处理`, `后处理中`, `待测试`, `测试中`, `已完成`, `方案终止`.
Testing alone does not imply completion.

Within `【配方与细节】`, use plain sublabels `原料用量：`, `操作条件：`, `观测与测试数据：`
only when relevant. Preserve units and precision; distinguish 实测, 计算值 and 历史引用.
For each record involving material use, add structured `materials` by operation with original
amounts, supported calculations, sources and pending information. Keep actual/planned amounts and
whole material/component bases separate. Preserve sample/step/branch identities for mother liquor,
dispersion, product and aliquots. Never replace original input with a conversion.

- Oral/brief notes: organize faithfully; do not invent actions, observations or experimental values.
- Complete unambiguous input: save directly, without mandatory full-draft approval.
- Missing measurements: mark `待补` and report together; save clear facts. Ask only about identity,
  units, sources or ambiguities that change the meaning of the record.
- “Same formula, except…”: cite the exact historical record ID and changes. Inherited targets or
  calculated scaled amounts are not actual balance readings.
- Photos: record material, visible reading and unit as 实测（天平读数）. If unclear, request only
  unreadable values/units, without guessing; preserve unambiguous information.
- Keep follow-up actionable. Include relevant reported problems, not boilerplate risks.

Cards have visible borders and light fills: synthesis `2563EB`/`EFF6FF`, treatment `16A34A`/`F0FDF4`,
testing `EA580C`/`FFF7ED`. Long cards may span pages. Keep stable within-day order.

## Save and monthly tracker

1. Prepare structured input using the contract; save authorized, clear records directly.
2. Save daily Word facts first, then refresh index and tracker. Retry using the same record IDs.
   Recover interrupted updates from Word; do not create duplicate records.
3. Tracker columns: 样品编号、项目、创建日期、当前步骤与状态、最近实验日期、记录入口.
   Sort creation date descending, then numeric sequence descending. Updates never change creation
   date. Links display dates/steps and open corresponding daily Word; recipes stay in daily cards.
4. Every month has its own tracker in that month's folder. On rollover keep the previous month's
   document there and create the new one with unfinished older samples plus current-month samples.
   Completed/terminated samples remain during their completion month. Backdated corrections must
   not roll the current view backwards or silently rewrite an older monthly tracker.
5. Tests of earlier steps must not regress the current process stage; where needed add a separate
   factual current-progress record while retaining the tested step on the test record.
6. Render and inspect changed Word using Documents. Return paths, sample IDs/states and pending
   data. Do not claim render verification without actual inspection.

Imported current-month records without an explicit state show `待确认` in the tracker. This is an
uncertainty label, not a guessed experimental state. Unknown older states are not automatically
carried forward; confirm their unfinished status before adding them to the current month's view.

## Context and downstream reports

Use [plans module](plans.md) when the user references a best plan or changes planned/actual conditions.
Resolve the existing process stage (not the sample's S01/S02) and its numeric plan version. A change
within an identified run starts from that run's version; a new adjustment defaults to the designated
best when context is clear. Allocate the daily record ID first, save changed conditions through the
plan tool with `mode: observed` and that source ID, then save the actual record with the resolved stage
ID as `plan_stage`, returned `plan_id`, and returned `version` as textual `plan_version`.
Plain reuse links to the existing version without a new one.
Record every clear condition change without automatically changing best. Inherited settings and
calculated quantities never become unreported measurements or completed operations. A future plan
alone creates no daily fact. Refresh recovers plan reverse links; export the affected plan afterwards.
Only the user's explicit designation changes a best marker; previous daily references stay pinned.

Use [context module](context.md) for background/target/reference maintenance and route readiness checks.
At record attribution check the relevant route. If incomplete, save clear facts and promptly ask
consolidated goal/stage/validation questions; acknowledge the question hash only after asking.
Keep the route pending until confirmed, and do not repeat unchanged pending questions.
Normal recording does not automatically rewrite background. Standard conditions do not prove this run's conditions.
Preserve the context version used for interpretation. Weekly/monthly reports query by date range,
preserve sample/step identities, deduplicate record IDs and access legacy sources only as needed.
