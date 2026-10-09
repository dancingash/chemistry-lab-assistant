# Lab Project Context

Resolve `{root}` (data) and `{program}` (installed package) through the entrypoint configuration.
Maintain `{root}/references/{project_id}.yaml`; references are outside skill folders and shared by
all three reporting skills. Use the installed virtual-environment Python and PyYAML for structured YAML operations.
Read `{program}/scripts/research_workflow_contract.md` for literature proposals, detailed backgrounds,
route-stage fields and deduplicated missing-route questions.

## Read and update only the relevant project

1. Resolve project ID/name from the request or matching existing reference. Ask only if ambiguous.
2. Read that YAML, preserving existing fields including `project_id`, `project_name`, `status`,
   `project_route`, `targets`, `chart_groups` and any user-defined keys. For a new project use
   `{program}/templates/project-context.yaml` as schema guidance; do not copy its example targets
   as facts. Missing goals/conditions remain explicitly pending, not guessed.
3. Accept natural-language descriptions and user-specified file/URL references. Read only the
   source sections relevant to the requested change. Keep source pointers with title, location,
   purpose, and optional section/page locator. Local locations should be relative to root where
   possible. Missing/unreadable references are marked pending; never claim to have read them.
4. Write an updated YAML candidate in the workspace and apply through
   `{program}/scripts/project_context.py --root ROOT update CANDIDATE.yaml --effective-date YYYY-MM-DD`.
   Use the stated effective date, or today's local date if none is specified, and report that default.
   Keep candidates under `work/project-context/`, outside official reference discovery. For literature
   additions/adaptations, run `preview`, show changes/basis/reason, and obtain user confirmation;
   use `--literature --review-digest HASH --confirmation TEXT`. Literature-based new projects follow
   the same flow. Implementation authorization is not confirmation of a future literature proposal.
5. The tool preserves the complete previous background under
   `references/history/{project_id}/vNNNN.yaml`, increments `context_version`, and records
   `effective_date` and `updated_at`. New projects start at version 1. Legacy unversioned projects
   are archived as version 1 on first change; their unknown historical effective date stays unknown.
6. Return the changed project, version, effective date and relevant pending information.

## Reference schema additions

`context_version`: positive integer; `effective_date`: ISO date; `updated_at`: timestamp.
`reference_sources`: list of mappings with `title`, `location`, `purpose`, optional `locator` and
`status` (`available` or `pending`). Existing files without these additions remain readable.
Read literature sources add `source_type: literature` and precise `locator`.
Build `project_background` with problem/goal, methods/limitations, hypothesis, metric references,
literature and actual experimental evidence; unknown content stays pending. Build `technical_route`
by stage purpose/method/variables, inputs/outputs, metrics/decision/next and alternatives, retaining
the concise `project_route` overview and existing process IDs.
At setup, attribution or planning, run `route --project ID`. If incomplete, continue saving facts and
promptly ask consolidated goal/stage/validation questions. Acknowledge the hash only after asking;
do not repeat unchanged questions. Confirm a route draft before marking it confirmed.

Preserve metric type (`min`, `max`, `range`, `qualitative`), values, units and required flags.
When a user changes one target, preserve other targets and chart groups. Clarify contradictory
goals or units; do not choose silently. The tool rejects missing existing keys to prevent accidental
partial replacement; explicit deletions require `--allow-remove` after the user requests them.

## How reports consume context

Background describes the project, not facts about a particular experimental run. Do not convert
experiment-plan conditions or a best marker into project targets. Use [plans module](plans.md) for
reusable operating plans, versioned condition changes and explicit best selection per process stage.
Project context changes do not rewrite existing plan snapshots.
Never convert standard temperatures, quantities or expected outcomes into measured data. Daily records cite
the version used when interpreting results. Old conclusions retain their original context; if a
comparison to current targets is requested, label it as a new comparison. Read historical versions
only when needed, using their version and effective date, not the current background by default.

Clear user-authored updates may save directly. Literature-derived background/route changes require
concrete preview confirmation. Updating a project does not authorize modifying historical reports,
other projects or sources.
