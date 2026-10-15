---
name: lab-rd
description: >
  Manage materials R&D projects, versioned experiment plans and user-designated best SOPs,
  calculate user-specified formulations and experiment batches with Excel recipe exports,
  record daily experiments and sample lineage, and prepare weekly PowerPoint and monthly
  spreadsheet reports. Use for lab research workflows and report queries.
---

# Lab R&D

One entrypoint for project context, plans, daily facts and reports. Read only the modules
needed for the current request; use several for a task that crosses workflows.

| Request | Read |
|---|---|
| Project setup, background, goals, literature, route | [context](references/context.md) |
| Create/change/reuse a plan, designate best, export SOP | [plans](references/plans.md) |
| Calculate formulations, gradients/repeats, export recipe Excel, confirm a batch into daily records | [formulations](references/formulations.md) |
| Record experiments, balance photos, corrections, sample queries | [daily](references/daily.md) |
| Weekly summary or PPT | [weekly](references/weekly.md) |
| Monthly summary or Excel | [monthly](references/monthly.md) |

## Installed program and private data

`{program}` is this SKILL.md's directory in an installed package. In a source checkout,
it is the repository root, two levels above this SKILL.md. Code and templates belong there.
`{root}` is private research data, resolved by `scripts/lab_config.py`: explicit `--root`,
`LAB_RD_DATA_ROOT`, legacy `REPORT_SKILLS_ROOT`, local configuration, then `~/.lab-rd/data`.
Do not infer data from the current working directory or from the author's environment.

Use `{program}/.venv/Scripts/python.exe` on Windows or `{program}/.venv/bin/python` on
macOS/Linux. Run `scripts/doctor.py` before first use. An offline `--skip-deps` package
must be completed by the installer before use. Never silently switch to another interpreter.
All examples and default templates are fictional or empty; do not treat them as lab facts.

Daily Word files are facts; project YAML holds versioned context; plan JSON holds condition
snapshots; indexes and reverse links are rebuildable. Stable sample, branch, step and record
IDs survive corrections, months and upgrades. Keep measured, calculated, planned and inherited
values distinct. A planned version does not create execution or a daily observation. Only an
explicit user designation changes a best marker. Context changes do not rewrite history.

Read `{program}/scripts/research_workflow_contract.md` for quantities, literature proposals
and routes when applicable. Read the records/plans contracts before their corresponding writes.
Keep project-specific rules in project YAML, not in these instructions. Never bulk-import history.

## Documents and report engines

Use the available Documents, Presentations and Spreadsheets supporting skills for their output
formats and visual QA. If missing, report the missing capability with setup instructions; continue
authorized data operations that do not require it. Never claim a report or render check succeeded
when its engine is unavailable.

For Node helpers, call `load_workspace_dependencies`, then supply its actual Node executable
and package directory to `scripts/run_node.py --node NODE --node-modules PACKAGES HELPER ...`.
Do not copy Codex runtime files, guess cache paths or depend on a repository node_modules link.
Full readiness: run doctor with those paths and the three supporting SKILL.md paths plus
`--require-full`. Environment readiness does not replace rendering and inspecting each output.

Use `scripts/demo.py --root DEMO_DIR` only when a demonstration is requested. Its explicit import
creates synthetic examples in a separate directory and refuses to overwrite existing research data.
