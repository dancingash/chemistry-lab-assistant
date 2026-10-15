# Experiment plan tool contract

Calculated formulation batches use `lab_formulations.py` and its contract. Each batch group pins a
normal numeric plan snapshot; independent repeats can reuse a snapshot with distinct daily records.
Batch JSON is additive and does not change this plan schema or the meaning of the best marker.

Use the installed virtual-environment Python. Put `--root ROOT` before the subcommand. JSON inputs use UTF-8.
`plans/PROJECT/STAGE/plan.json` holds immutable full snapshots, change events, best selection history,
rebuildable daily links, idempotency results and export checksums. Its schema is version 1. Process IDs
are stable ASCII identifiers, not sample-step numbers. One process has one best marker across targets.

## Commands

- `list --project PROJECT`: discover stage IDs, names and best markers without loading all conditions.
- `show --project PROJECT --stage STAGE [--version best|NUMBER]`: full resolved snapshot and daily links.
  Missing best is an error, never a fallback to latest. `history` with project/stage returns version
  metadata, change events, best history and daily links without duplicating full snapshots.
- `create INPUT.json`, `derive INPUT.json`, `set-best INPUT.json`: atomic structured mutations below.
  These do not write daily facts or generate Word; call `export` afterwards.
- `export --project PROJECT --stage STAGE [--reviewed REVIEW.json]`: regenerate overview, concise
  condition notes and designated best SOP (or clearly labelled pending draft).
  Both known and pending export hashes allow interruption recovery; Word files can be rebuilt from JSON.
- `preview INPUT.json --action create|derive`: read-only differences and review digest. Literature
  changes require the digest and user confirmation; see `research_workflow_contract.md`.

All mutations take `project_id`, `stage_id`, stable `operation_id` (UUID recommended), and optional
ISO `date` (defaults to today's local date, returned in result). Reuse the EXACT input and operation ID
after an uncertain response, including whether date was omitted. Identical retry returns its original
result even after best changes; a reused operation ID with different content fails. A separate attempt
uses a new operation ID. Results contain `plan_id`, `version`, `best_version`, `date`, and `created`.
Derivation additionally returns `base_version`; best selection returns `previous_best`.

## Content and changes

Creation also takes `stage_name`, `content`, optional `mode` (`planned` by default; `observed` for
reported actual conditions) and `source`. Source permits textual `description`, `location`, `record_id`,
`sample_id`, `context_version`; do not invent a source that was not read. `observed` requires a stable
source record ID allocated before daily saving. This is provenance of the report, not proof that every
inherited condition was executed.

Content accepts:

- `purpose`, `scope`: nonempty text; omitted becomes 待补.
- `materials`, `equipment`, `operations`, `conditions`, `controls`, `tests`, `acceptance`: ordered maps
  of descriptive names to nonempty text. Equipment/control/acceptance fields are optional for ordinary
  conditions but necessary for a complete SOP. Omitted legacy fields remain readable as pending.
  Omitted maps are empty and display 待补. Keep operations in execution order. Distinguish similarly
  named conditions by step, e.g. 反应温度 versus 干燥温度. Values retain units and precision.
- `pending`: list of unresolved information; defaults to an empty list. Empty content sections still
  appear in the Word pending list. Never use numeric-only values whose units are unknown.

Derivation takes `base_version` (a positive integer, or `best` resolved atomically), `patch`, optional
`mode` and `source`. Prefer the exact numeric baseline already read. Only supplied map entries change;
omitted entries and sections survive unchanged. `null` explicitly deletes a named existing map entry
only when the user requests it. `purpose` and `pending` replace as whole values. Each version records
full content, its base and before/after changes. Unknown fields fail rather than disappearing silently.
To change execution order, additionally supply `operation_order` alongside `patch`, listing every
remaining operation name exactly once. The order becomes part of version identity and change history;
otherwise retained steps keep their order and newly added steps append at the end.
Identical complete content reuses an existing version; a new operation still leaves a provenance event.

Synthetic example only, never save it to a real project:

```json
{
  "project_id": "DEMO", "stage_id": "peg", "operation_id": "unique-operation-id",
  "date": "2026-09-20", "base_version": 1,
  "patch": {"conditions": {"反应温度": "80 ℃"}},
  "mode": "planned", "source": {"description": "用户要求基于最优版本调整温度"}
}
```

`set-best` takes numeric `version` and `instruction`, the user's explicit designation text. No automatic
ranking, metric threshold or creation rule sets best. Switching best never changes any snapshot or daily
reference. Initial best is null; designating the same version again does not duplicate marker history.

## Daily integration and recovery

Daily save accepts optional strings `plan_stage` (stage ID), `plan_id` (`PROJECT:STAGE`, returned by the
tool), `plan_version` (positive integer as text). Provide all three or none. They become visible
`【方案工序】【方案编号】【方案版本】` labels, parsed fields and indexed metadata. The referenced snapshot
must exist and match the daily project's ID and stage. Never persist `best` as a daily reference.

Order: allocate record ID → save a changed plan if needed → save factual daily record referencing the
returned version → refresh/index/tracker → export affected plan. A retry reuses both IDs. Daily refresh
also reconciles reverse links, including corrected or removed references, without creating versions.
If a plan saved but the daily save failed, it remains an unlinked snapshot, not an executed experiment.
If daily/index saved but reverse linking failed, refresh recovers from Word. Old records need no plan
fields and remain valid. Historical best changes do not rewrite daily facts or past monthly trackers.

## Export safeguards

Exports use `方案总览.docx`, concise `versions/vNNNN.md` and, only after explicit best designation,
`SOP.docx`. Complete SOPs are retained as `sop/vNNNN.docx`; best changes mark prior SOPs historical.
Missing necessary purpose/scope/materials/equipment/operations/conditions/controls/tests/acceptance or
explicit pending information produces SOP待补稿, not a formal SOP. Snapshots stay complete in JSON;
ordinary versions need no formal Word. Existing legacy version Word files are not rewritten.
Literature sources add textual source_type/title/locator/original_method/adaptation_reason alongside
location; confirmed mutation takes top-level review_digest/confirmation. CLI writes return route checks.

Unknown or hand-edited Word blocks export BEFORE replacing any document in the batch. Read and reconcile
the reported file, derive a new version if needed, then supply a JSON map such as
`{"方案总览.docx": "EXACT_INSPECTED_SHA256"}` to `--reviewed`. This asserts review already occurred;
never calculate the hash and bypass the conflict without reading the edits. Only reviewed bytes are
backed up to `manual_edits/HASH.docx` before replacement. Locked Word errors leave JSON intact; close the
file and retry export. A leftover `.write.lock` requires confirming that its process is no longer writing
before removing that exact lock. Never delete plan history as a recovery step.

Query/export may show stale reverse links after out-of-band Word edits; run daily `refresh` first.
Word views are derived; raw hand edits do not silently change the authoritative plan or best marker.
