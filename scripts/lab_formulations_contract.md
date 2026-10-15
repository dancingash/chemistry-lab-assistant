# Formulation batch contract

Use the installed virtual-environment Python. `--root ROOT` precedes the subcommand.
Batch JSON under `plans/PROJECT/STAGE/batches/BATCH.json` contains immutable numbered recipe
revisions, pinned plan snapshots and a recoverable operation journal. Completion facts remain
authoritative in daily Word; Excel is a calculated export, never an automatic source of facts.

## Commands

- `preview INPUT.json`: read-only arithmetic and group expansion. No directories or samples created.
- `save INPUT.json`: save a numbered revision and each distinct recipe as a planned plan version;
  repeated groups share the full-content-deduplicated plan snapshot. Export the stage overview.
- `list --project PROJECT [--stage STAGE]`: locate batches without returning all calculations.
- `show --project PROJECT --stage STAGE --batch BATCH [--revision NUMBER]`: recipe and completion links.
- `export --project PROJECT --stage STAGE --batch BATCH [--revision NUMBER] --node NODE
  --node-modules PACKAGES [--output FILE.xlsx]`: generate two-sheet Excel, compare every numeric
  formula to the Decimal engine, recalculate, and render both sheets. Existing outputs are refused
  to preserve hand edits. Inspect every image listed in the adjacent `.qa.json` before delivery.
- `complete --project PROJECT --stage STAGE --batch BATCH INPUT.json`: user-confirmed execution only.

IDs follow existing project/stage safe ASCII identifier rules. Save and complete require a stable
`operation_id`; retry EXACT input after failure. Different payload with the same ID is rejected.
An unfinished write must be recovered before another operation on that batch. Do not delete its
journal. Batch locks and a global completion lock guard sample allocation; stale locks require
checking that no writer is active before removing the exact lock file.

## Save input

Required: `project_id`, `stage_id`, `batch_id`, `operation_id`, `description` (original requirements),
`recipe`. Optional: `stage_name`, ISO `date`, numeric `base_version`, `plan_content`, `variables`,
`combination`, `repeats` (positive integer, default 1). With an existing stage, resolve its best or
use the user-selected numeric baseline; no best must not silently mean latest. A new stage's first
group creates its initial version; subsequent groups derive from that first snapshot. Unspecified
conditions inherit the pinned baseline. Recipe materials replace the baseline material map.
`plan_content` uses the existing plan content contract (operations, tests, conditions, etc.).
Exact numeric inputs and material property sources also enter the plan snapshot, so two inputs
that round to the same displayed amount do not accidentally collapse into one version.

Each `recipe.materials` row has `id`, `name`; optional `material_type` (default unknown), `role`,
`component`, `formula`, `properties`. Material names and IDs must be unique. Properties use
`{value: DECIMAL_STRING, unit: UNIT, source: TEXT}`. Existing quantity properties are supported,
plus `solids` (% or fraction), `functionality` (1), `equivalent_weight` (g/eq). Missing constants
remain pending. Explicit pure compounds alone may use visibly labelled nominal purity 1.

`recipe.calculations` is an ordered dependency list. A material is assigned once; dependent
calculations use prior outputs. Every quantity and property parameter is `{value, unit, source}`.
Ratios are nonnegative decimal strings with the original description as their source.

| mode | Additional keys and calculation |
| --- | --- |
| fixed | `material`, `quantity`: specified mass/volume/amount |
| mass_ratio | `total` (mass), `ratios` (material ID to number): allocate total by ratio sum; `basis: component` with `content_property: solids|purity` treats total and ratios as effective-component masses and inverts supplied content fractions |
| mass_fraction | `total` (mass), `fractions` (ID to %/fraction parameter), `basis` (material default or component); component basis additionally requires `content_property` purity or solids |
| solids | `total` (mass), `total_basis` (wet default or dry), `fraction` (target solids), `ratios` (dry-component mass ratios), `solvent`: invert each material's supplied solids fraction, then supplement mass; solvent must have explicitly sourced solids=0 |
| molar_ratio | `reference` (previously assigned material), `ratios` including positive reference ratio: use exact compound molar mass/purity or identified solution component concentration |
| equivalents | `reference`, `ratios`: use sourced functionality times molar amount or equivalent weight; for pure compounds apply purity, for other materials equivalent weight must explicitly describe whole supplied material in g/eq, not an unidentified component; no inferred functionality |
| dilution | `material` (identified solution), `stock`, `target` (same concentration family), `final_volume`: stock volume from c1V1=c2V2, with final-volume instruction; do not infer additive solvent volume |
| scale | `quantities` (ID to quantity parameter), exactly one of `factor` (unit 1) or `target_total` (mass): scale each original amount; total-mass scaling requires mass inputs or sourced density for volume inputs |
| make_up | `material` (supplement), `total` (mass), `members` (distinct already-assigned IDs excluding supplement): subtract whole-material masses; density needed for volume inputs |

Pure-compound molar calculations do not apply to undefined mixtures, dispersions or unknown
materials. Density alone does not reveal solute content. Negative supplement quantities, zero
denominators, incompatible units, fractions above 100%, duplicate assignments and impossible
dilutions fail explicitly. Missing properties preserve independently determined results.

Each variable is `{name, path, values}`. `path` is a list addressing an existing leaf INSIDE recipe,
e.g. `["calculations",0,"ratios","A"]`. Multiple variables require `combination: zip|product`;
zip requires equal lengths. `repeats` applies to each combination. Stable group IDs are
`G001-R01`, `G001-R02`, etc., scoped to a batch revision. No sample ID exists yet.

Synthetic arithmetic example, never import into real research data:

```json
{
  "project_id":"DEMO", "stage_id":"mix", "stage_name":"软件测试混合",
  "batch_id":"trial", "operation_id":"save-unique", "description":"软件测试：A:B=1:2，总量30g，重复两次",
  "recipe":{
    "materials":[{"id":"A","name":"测试材料A"},{"id":"B","name":"测试材料B"}],
    "calculations":[{"mode":"mass_ratio","total":{"value":"30","unit":"g","source":"用户要求"},"ratios":{"A":"1","B":"2"}}]
  }, "repeats":2
}
```

## Completion input and recovery

Required: `operation_id`, `confirmation` (user's actual completion words). Optional `revision`
(latest by default), `groups` (all by default), `timezone` (numeric UTC offset, default +08:00),
`defaults`, `reports` (group ID to group-specific report). Group report overrides defaults.
Only the assistant interprets the user's natural language; never generate confirmation yourself.

Report fields: `date`, `created_date`, `sample_id`, `step`, `experiment_type`, `state`, `today`,
`follow_up`, `details`, `context_version`, `as_planned` (boolean), `materials` (actual rows per existing contract),
`observed_patch` (actual condition changes per plan patch contract), `source_sample`, `source_step`.
Dates are explicit ISO dates in persisted records. Omitted date is resolved ONCE in the requested
conversation timezone, returned in results and visibly disclosed in daily details. New synthesis
sample creation date defaults to the experimental date, disclosed as provisional when not supplied.
Use the true synthesis date when known. Existing sample IDs retain their creation dates. Treatment
and testing require an existing sample identity; branch inputs retain both source fields.

Defaults: synthesis, S01; completed user-reported work has state 待测试 when the pinned plan lists
tests, otherwise 已完成. Override state when the user's reported follow-up requires another state,
e.g. 待后处理. Completion refers to the reported operation; do not invent test results or completed
operations. `as_planned` records user-confirmed conditions, never balance readings. Actual quantities
are additional rows; calculated planned rows remain planned. Reported actual quantities or
`observed_patch` derive an observed plan with the daily record ID before saving the daily card.

Daily fields `batch_id`, `batch_revision`, `batch_group` are optional as a complete trio, together
with a numeric plan reference. They survive parsing, query and cold index rebuild. A correction uses
the original record ID through the daily correction workflow; re-confirming a completed group with
different report data is rejected rather than overwriting facts. Re-confirming with identical or no report data
returns existing links. Different completion dates are saved separately.

Durable order: reserve record/sample IDs and exact inputs → journal each plan operation → save
daily Word → refresh/index/tracker and reverse links → export plan → persist completion links.
Word success followed by index/export failure is recoverable using the same operation input.
Excel creation/export is independent: an engine failure does not discard saved recipes or facts.
Hand-edited daily documents, trackers and plan exports retain existing review protections.
