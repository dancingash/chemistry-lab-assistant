# Shared research workflow: quantities, literature and routes

Apply to new records; enrich historical records only when invoked or explicitly requested. Do not
bulk-rewrite project YAML, legacy Word, immutable plan snapshots or past reports.

## Material tables and conversions

`lab_records.py save` accepts optional `materials`, an ordered list for feed, stock solution,
dispersion, aliquot or product. Group by operation; actual and planned amounts use separate rows.
Tests with no reported material use need no invented reagent list. Keep narrative details as well.

Each row requires `operation`, `name`, `role`, `original`, `quantity_kind` (`actual`/`planned`) and
`material_type` (`pure`/`solution`/`dispersion`/`mixture`/`unknown`). Optional `formula`, `component`,
`sample_id`, `sample_step`, `source_record_id`, `note` preserve identity and state/provenance.
`measurements` contains `{kind, value, unit, basis, source}`; `kind` is `mass`/`volume`/`amount`,
`basis` is `material` (whole material, default) or `component` (identified component).
Use decimal strings to retain reported precision; `original` retains the user's exact wording.

Synthetic software example, not an experimental recipe:

```json
{"operation":"投料","name":"测试纯物质","role":"原料","original":"称取 1.00 g",
 "quantity_kind":"actual","material_type":"pure",
 "measurements":[{"kind":"mass","value":"1.00","unit":"g","basis":"material","source":"用户报告称量"}],
 "properties":{"molar_mass":{"value":"100","unit":"g/mol","source":"测试常数"}}}
```

`properties` maps each property to `{value, unit, source}`:

| Property | Units | Meaning |
|---|---|---|
| molar_mass | g/mol | Exact compound/component, including hydrate or salt form |
| density | g/mL, g/ml, g/L | Whole material; cite applicable temperature/state |
| purity | fraction, % | Pure reagent mass correction for compound amount |
| molarity | mol/L, mmol/mL, mmol/L | Identified component amount per whole volume |
| mass_concentration | g/mL, g/L, mg/mL | Identified component mass per whole volume |

Mass units: g/mg/kg/ug/μg/µg; volume: mL/ml/L/uL/μL/µL; amount: mmol/mol/umol/μmol/µmol.
Use constants only from supplied or verified authoritative material sources, never another sample
or project targets. `pure` requires explicit identification as a pure compound; otherwise use
`unknown`. Declared pure compounds with no impurity information use nominal purity 1, visibly labelled.
Solution density yields total mass, not solute mass. Only identified solution components get amount
conversions; dispersions, composites and unknown materials get no inferred molar amount.

The helper retains original measurements and computes only supported conversions with provenance
chains. Independent inputs differing by more than 0.5% from a conversion are shown as conflicts,
with calculated outputs withheld. This is rounding tolerance, not instrument uncertainty or permission
to revise measurements. Report conflicts and missing properties together while saving clear facts.
Calculated displays use up to eight significant digits; do not claim these as measured precision.

The nested table and XML payload both live in daily Word; cold rebuild needs no JSON sidecar.
Manual table changes block parsing until table/payload reconciliation; do not remove the payload to
bypass review or regenerate from old values. Replacing saved original material data requires reading
the before/after difference and user confirmation, then `reviewed_materials` set to the returned
old-data SHA256. Omitting `materials` during narrative-only correction preserves the table.

Same sample ID does not imply identical state or amount. Read the matching step, branch, date,
operation and basis before reuse. A new weighing after treatment is a new observation; another
representation of the same observation must reconcile with its source record. Cite its ID in
`source_record_id`. Never sum planned amounts as actual consumption.

## Literature proposals

Separate original literature conditions, proposed adaptations and reported execution. Read the source
first; retain title, file/URL, page/section/table locator and supporting claim/method. Unread sources
are pending and cannot substantiate a background conclusion or method.

Project candidates belong under `work/project-context/`, outside the official reference glob. Run
`project_context.py --root ROOT preview CANDIDATE.yaml`, show differences, basis, adaptation reason
and pending information. After confirmation run `update CANDIDATE.yaml --effective-date DATE
--literature --review-digest HASH --confirmation TEXT`. New/changed `source_type: literature`
sources also trigger checks automatically. Use `--literature` when adapting from existing literature
even when the source list is unchanged. Candidate or current-context changes invalidate the hash.
Direct clear user-authored changes unrelated to literature retain the existing direct-save flow.

Plan sources use textual `source_type: literature`, `title`, `location`, `locator`, `original_method`,
`adaptation_reason`. Run `lab_plans.py --root ROOT preview INPUT.json --action create|derive`, show
differences and rationale, then add `review_digest` and user `confirmation` to the SAME input before
applying. Changed content/baseline invalidates confirmation. Retry exact operation ID/payload after an
uncertain result. Background and plan are separate writes: confirm both concrete proposals.

## Background and route readiness

Preserve existing fields. `project_background` holds problem, application goal, methods, limitations,
hypothesis, metric references, literature evidence and actual experimental evidence. `targets` remains
the authoritative metric map; reference names instead of duplicating thresholds.

`technical_route` holds `status: pending|confirmed`, `stages`, `alternatives`. Stages have stable
ID/name plus `purpose`, `method`, `variables`, `inputs`, `outputs`, `metrics`, `decision`, `next`.
Align with existing plan process IDs; sample S01/S02 remain independent. Keep `project_route` as a
concise overview for old consumers. Unknown details remain pending.

Run `project_context.py --root ROOT route --project ID` at project creation, record attribution and
plan generation. Legacy prose is usable background but not a confirmed stage route. If pending,
save facts and consolidate goal/stage/validation questions with other needed clarification; present
a route draft and confirm it before recording `status: confirmed`.

Only AFTER asking, run `route --project ID --acknowledge --question-id HASH`. It saves communication
state under `work/project-context/`, not official YAML. Unchanged pending questions are not repeated;
changed goals/routes reopen the check. Daily-save/plan-write CLI results also return route checks.

## Downstream interpretation

Weekly/monthly reports use saved context version/effective date and pinned numeric plan version.
Candidates in `work/`, suggested adaptations and incomplete SOPs are not confirmed routes or evidence
of execution. User-designated best is selection status, not proof of passing tests. Match sample
branch/stage and distinguish measured, calculated and planned values in summaries.
