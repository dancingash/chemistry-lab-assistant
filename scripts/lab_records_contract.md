# Daily record tool contract

Use the installed virtual-environment Python, with `--root ROOT` before the subcommand. Relative document paths must stay
inside ROOT. Word holds facts; index.json holds metadata and content hashes.

## Structured save

`lab_records.py --root ROOT save INPUT.json` accepts one day's `{"records": [...]}`.
One record describes one sample and step. Required string fields:

- `record_id`: stable unique ID (UUID recommended); reuse for corrections/retries.
- `date`, `created_date`: ISO dates; retain actual sample creation date.
- `project`: project ID followed by name.
- `sample_id`: main or branch ID; `step`: S01, S02, etc.
- `experiment_type`: 合成 / 后处理 / 测试.
- `state`: 合成中 / 待后处理 / 后处理中 / 待测试 / 测试中 / 已完成 / 方案终止.
- `today`, `follow_up`: faithful operation and next action; 待补 is permitted.

For clear work with an unknown sample ID, preserve a descriptive `sample_id` such as
`昨日 PEG 接枝树脂（原编号未提供）` and set `created_date`, `step` and `state` all to `待确认`.
The daily card saves, but no sample tracker row is created. Correct the same `record_id` later
when identity is confirmed; do not assign a guessed identifier.

Optional strings: `details`, `risk`, `context_version`, `source_sample`, `source_step`.
Optional structured `materials` lists per-operation original quantities, properties and sources;
see `research_workflow_contract.md`. This field is a list, unlike the textual fields. Queries and
cold rebuild retain original and calculated values from Word. To correct saved material data, review
the difference and submit `reviewed_materials` with the old-data hash after user confirmation.
Omitting `materials` preserves the old table on narrative-only updates.
Both source fields are required for branches. Put measurements, units, actual/calculated/inherited
qualifiers and source record IDs in details. These become visible labels in Word.

Optional plan reference strings: `plan_stage`, `plan_id`, `plan_version` (all three together).
Use the process ID, tool-returned `PROJECT:STAGE` and positive numeric version as text; never `best`.
The referenced snapshot must exist and match the daily project and stage. They are written as visible
方案工序、方案编号、方案版本 labels and retained during query and index rebuild. See
`lab_plans_contract.md` for condition changes and ordering. `refresh` recovers reverse plan links from
daily metadata, including corrected references. This adds no experiment and does not change best.

```json
{"records": [{
  "record_id": "example-stable-id",
  "date": "2026-09-17", "created_date": "2026-09-16",
  "project": "DEMO 示例项目", "sample_id": "DEMO-20260916-1",
  "step": "S01", "experiment_type": "后处理", "state": "待测试",
  "today": "已完成干燥。", "details": "操作条件：温度、时间待补。",
  "follow_up": "安排测试，具体指标待补。"
}]}
```

This is synthetic example data; never insert it into production reports. Saves replace matching IDs
in place and append new IDs. Use a targeted Documents edit for handwritten paragraphs, images,
unknown labels or customized layouts, preserving IDs; then refresh instead of regenerating the file.

## Query and recovery

- `query --sample ID [--step S01] [--kind 合成]`: exact identity, not substring matching.
- `query --start YYYY-MM-DD --end YYYY-MM-DD [--out FILE.json]`: period records, including
  cross-month weeks. Returns records and read_log; records retain fields consumed by summaries.
  Output omits duplicate raw text and known label mappings; use `--full` only for diagnostics.
- `refresh`: discover daily files and reparse changed documents only.
- `refresh --legacy RELATIVE_PATH`: explicitly register a chosen authoritative legacy Word;
  repeat for different months. Only one legacy snapshot per month, never auto-pick a version.
- `migrate-day --date YYYY-MM-DD --legacy RELATIVE_PATH`: copy every record on that date from
  a registered monthly Word into its daily card. Preserve the old source, exact record text and
  its provenance. The index excludes copied originals from queries and period summaries. Missing
  sample IDs remain descriptive and unlinked to a tracker row until confirmed. Idempotent retry
  checks the recorded origin IDs.
- `replace-legacy --old RELATIVE_PATH --new RELATIVE_PATH`: switch a selected legacy source
  after resolving conflicting versions; neither Word is modified.
- `rebuild [--legacy RELATIVE_PATH]`: rebuild from daily files and explicit legacy selections.
  With a lost index, re-identify old authoritative sources from tracker links/user context.
- `tracker --month YYYY-MM`: regenerate `report/YYYY-MM/项目追踪表_YYYY年MM月.docx` or create
  a new month's view. The prior month's file stays in its folder. A legacy root tracker can be
  read during transition but is no longer the current write target.

Content hashes detect edits even with unchanged mtime. Parsing happens locally, while only selected
records enter model context. Duplicate IDs with different content fail; identical old records receive
stable content IDs. Retain those IDs when explicitly migrating a record. Similar unidentified records
are not automatically merged. Empty query results may require a scoped historical lookup.

## Manual changes and interrupted writes

Daily Word is authoritative for experimental facts. If the tracker was edited, inspect both documents,
write confirmed factual corrections into the daily card through a targeted edit, then use
`tracker --month YYYY-MM --accept-reviewed`. This flag asserts review already happened; never use
it simply to bypass an error. Formatting-only tracker edits do not require reconciliation.

Daily, index and tracker files use individual atomic replacements, not a multi-file transaction.
After interruption run refresh then tracker; retries reuse record IDs. A corrupt/locked Word errors
instead of returning empty data. Keep the current month during backdated edits; archives remain intact.

Legacy records without state show 待确认 during their recorded month and are not automatically
carried into later months until unfinished status is confirmed. Missing identities remain queryable
by date but cannot be assigned to a sample by guess. Testing an older step must not regress current process status; preserve
the tested step and, if necessary, add a separate factual current-progress record.
