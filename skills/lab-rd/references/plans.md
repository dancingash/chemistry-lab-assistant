# Lab Experiment Plan

For structured formulation calculations, gradients/repeats and subsequent batch completion, also
read [formulations](formulations.md). Batch calculations pin numeric plan versions; no sample or daily
fact is created until user-confirmed execution. Repeated groups can share the same plan snapshot.

Resolve `{root}` (data) and `{program}` (installed package) through the entrypoint configuration.
Use `{program}/scripts/lab_plans.py` with the installed virtual environment; use `load_workspace_dependencies` for Node and document engines.
Read `{program}/scripts/lab_plans_contract.md` before saving, linking records or exporting.
Read `{program}/scripts/research_workflow_contract.md` for literature confirmation and route checks.
Use Documents for Word generation and render inspection. Scheme data lives outside skills in
`{root}/plans/{project_id}/{stage_id}/`; `plan.json` is authoritative for plans, daily Word for facts.

## Minimal input and stable baselines

- Accept short requests such as “基于 PEG 接枝最优方案，把温度改为 80 ℃，其他不变”.
  Resolve project and process stage from the conversation, corresponding project background and
  `list --project PROJECT`. Reuse the existing stage ID; do not equate a process stage with a sample's S01/S02.
- Maintain one best version per project/process stage, including across different target gradients.
  “Latest” and “best” are separate. Only an explicit user designation authorizes `set-best`; do not
  choose a winner from test results, create an initial best automatically, or silently change the marker.
- Resolve “best” via `show`, inherit all unmodified content, and save only the stated changes with
  `derive`. Use the resolved numeric base in the input. A later best change cannot alter this snapshot.
  “Again based on best” starts from best again, not the latest attempt. An explicitly named version
  or sample takes precedence over a default baseline; retrieve its exact reference.
- When the user omits a baseline for a new adjustment, use this stage's designated best and state
  which version was used. For a change during an already identified experimental run, use that run's
  pinned version. If no best/run reference exists, ask only for the required baseline.
- Ask one consolidated question only for unresolved project/stage/baseline identity, conflicting units,
  or conditions whose ambiguity changes meaning. Save clear information; leave other gaps as 待补.
  Do not ask the user to fill a template, invent quantities, or silently scale all ingredients.
- First-time creation can read a user-selected document, sample or brief description. Preserve exact
  sources and units; historic samples keep their original IDs. Do not bulk-import or infer an optimum.
- Before generating plans, check the relevant route. If incomplete, preserve clear conditions and
  discuss goals, stages and validation promptly; proposed routes stay pending until confirmed.
- Literature-derived creation/adjustments retain original methods and locators. Display the concrete
  adaptation/difference first, then save with the preview hash and user's confirmation.

## Plan changes and actual work

1. A future experiment creates a `planned` version only. It does not create a sample, daily fact or
   completion state. Report only the new version, baseline, key change, unchanged best and missing data.
2. During daily recording, reported changes to ingredients, operations, conditions or tests become an
   `observed` derive operation from the referenced version. Allocate/reuse the daily record ID first
   and place it in the source; do not drop a clear change merely because it is temporary.
3. Store the plan snapshot, then save the actual daily record using [daily module](daily.md): use the resolved
   stage ID as `plan_stage`, returned `plan_id`, and returned `version` as textual `plan_version`.
   Explicit reuse of unchanged conditions links to the
   existing version without deriving an identical attempt unnecessarily. Tool-level deduplication also
   reuses matching full content. Multiple samples can reference one version with separate daily IDs.
4. Inherited conditions remain plan settings. Actual readings, calculations and inherited values stay
   distinguishable in daily details. “As planned” can substantiate reported execution, but cannot create
   balance readings, completed steps, yields or results that were never reported.
5. Daily `refresh` rebuilds reverse links from daily Word metadata. If any later save fails, keep the
   successful plan operation/record IDs, retry the same input and refresh; do not create another version
   or assert execution simply because a plan exists. Corrections use the same daily record ID and
   a new plan operation if its conditions changed. Old snapshots remain available.
6. Export the affected stage after a successful create/change/designation/daily link update. Refresh
   relevant daily records before querying evidence or recovering links; do not scan all historical Word.

## Word and hand edits

`export` writes `方案总览.docx` with best status/change comparisons and concise
`versions/vNNNN.md` condition records. Only a user-designated best generates `SOP.docx`;
complete SOPs are also retained under `sop/vNNNN.docx`. Prior exported Word versions remain untouched.
SOPs include purpose/scope, material amounts, equipment, ordered operations, conditions, control points,
testing/acceptance, version designation and experiment/source evidence. Missing necessary information
produces a clearly marked SOP待补稿; never invent conditions or label it formal. Best changes mark
published SOPs as historical without changing snapshots or old daily references.
Display every condition with its meaningful units; preserve operation order and material precision.

If export reports hand edits, read that exact Word first. Incorporate clear user-authored changes into
a new version or preserve the intentional document edits; never blindly acknowledge the hash. Resolve
ambiguous edits in one short question. After reconciliation, pass only the inspected file's exact hash
through `--reviewed`. The tool keeps a byte-for-byte copy under `manual_edits` before replacement.
Render and inspect all changed deliverable Word files through Documents; do not claim visual QA without it.
If its packaged `render_docx.py` fails because LibreOffice is unavailable, inspect that error, then use
bundled Node with `{program}/scripts/render_lab_plan_docx.mjs INPUT.docx OUTPUT_QA_DIR`. This fallback
uses the bundled document engine locally. Inspect every page in its `render-report.json`; report the
engine used accurately. Keep QA files separate from plans and do not read stale pages from prior renders.

Project targets/background stay under [context module](context.md). Weekly/monthly reports count actual daily
records, not plan versions; a new best does not rewrite previous experiments or conclusions.
