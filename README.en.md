# Chemistry Lab Assistant

[简体中文](README.md) | **English**

A Chinese-first materials research workflow for Codex. The single `$lab-rd` skill manages project context, versioned experiment plans, formulation batches, daily experiment records, and sample traceability, and produces Word documents, weekly PowerPoint reports, and monthly Excel reports.

Describe your research task in natural language, and the assistant uses the relevant modules to record, calculate, and export your work. Program files, templates, and experimental data are stored separately. After installation, you can move or remove the repository checkout.

## Features

| Feature | Capabilities | Data or output |
| --- | --- | --- |
| Project context | Maintain objectives, stages, technical routes, and context versions | Project YAML and version history |
| Experiment plans | Adjust conditions, inherit a chosen version, and record the best plan explicitly selected by the user | Plan JSON, Word plan overviews, and SOPs |
| Formulations and batches | Calculate quantities, expand gradients and independent replicates, and save batch revisions | Batch JSON and two-sheet formulation workbooks |
| Daily experiment records | Record actual operations, quantities, test results, and missing information | Daily Word records and sample tracking documents |
| Sample traceability | Link samples, branches, steps, plan versions, and formulation groups | Rebuildable indexes and queries across dates |
| Weekly and monthly reports | Summarize recorded work while preserving sample and test-step details | Weekly PowerPoint and monthly Excel reports |

The formulation module supports mass ratios, mass fractions, dry- and wet-basis solids content, active-ingredient conversions, molar ratios, equivalents, concentration dilution, formulation scaling, and solvent addition to reach a target mass. Required material properties retain their sources; missing values remain marked as pending.

## Quick installation

You need Python **3.12–3.14**, Codex with skill support, and an internet connection to download Python dependencies. Windows, macOS, and Linux are supported. The installer does not require administrator privileges. On the first installation, it downloads the pinned dependencies in `requirements.lock` and creates a separate virtual environment.

Clone the repository and enter its root directory. For a private repository, configure GitHub access first.

```sh
git clone https://github.com/dancingash/chemistry-lab-assistant.git
cd chemistry-lab-assistant
```

Run the installer:

Windows PowerShell:

```powershell
py -3.12 scripts/install.py
```

macOS / Linux:

```sh
python3 scripts/install.py
```

The default skill location is `$CODEX_HOME/skills/lab-rd`, or `~/.codex/skills/lab-rd` when `CODEX_HOME` is unset. The default data location is `~/.lab-rd/data`. The installer creates empty data directories and does not import examples. You can choose your own installation and data directories:

```sh
python3 scripts/install.py --skills-dir /path/to/codex/skills --data-dir /path/to/research-data
```

On Windows, replace `python3` with `py -3.12` and quote paths containing spaces. Reopen Codex's skill discovery interface and check that “研发助手” appears. If the current chat still shows the old skill list, start a new chat.

The installed program directory contains `SKILL.md`, `scripts/`, `templates/`, `examples/`, `.venv/`, `local.json`, and an installation manifest. These files no longer depend on the checkout. In the commands below, `<program-dir>` means the installed `lab-rd` directory.

## Environment checks and report capabilities

Windows:

```powershell
& "$env:USERPROFILE/.codex/skills/lab-rd/.venv/Scripts/python.exe" "$env:USERPROFILE/.codex/skills/lab-rd/scripts/doctor.py"
```

macOS / Linux:

```sh
~/.codex/skills/lab-rd/.venv/bin/python ~/.codex/skills/lab-rd/scripts/doctor.py
```

Adjust these paths if you use a custom installation directory or `CODEX_HOME`. `core_ready` means the Python tools and templates are available. `full_report_ready` additionally requires three supporting skills and Codex's Node document runtime. Core capabilities let you maintain project context, plans, and daily record data; they do not establish that the full reporting environment is ready.

Full reporting requires the **Documents, Presentations, and Spreadsheets** supporting skills. If any are missing, install them through Codex's skill or plugin management. This project does not bundle those plugins. In Codex, enter:

> Use $lab-rd to check the full reporting environment. Call load_workspace_dependencies, then pass the actual Node executable, Node package directory, and the SKILL.md paths of the three supporting skills to doctor.py --require-full.

The corresponding command interface is:

```sh
<installed-python> <program-dir>/scripts/doctor.py --require-full \
  --node <actual-node-path> --node-modules <actual-node-package-dir> \
  --documents-skill <Documents-SKILL.md> \
  --presentations-skill <Presentations-SKILL.md> \
  --spreadsheets-skill <Spreadsheets-SKILL.md>
```

Environment checks do not write experimental data or replace rendering and visual inspection of each deliverable. Word documents use the Documents renderer by default. If it is unavailable, the plan module offers an alternative rendering path through Codex's document runtime. Presentations handles PowerPoint creation and verification; Spreadsheets handles Excel creation and verification. Missing fonts or renderers must be reported explicitly.

## Workflow

Start with “create a project → prepare a plan or formulation → perform experiments and record them → query traceability → generate reports.” For an existing project, continue from the relevant step.

Invoke `$lab-rd` in natural language, or let Codex select the skill automatically:

| Task | Example prompt |
| --- | --- |
| Create a project | “Use $lab-rd to create research project NEW01. Record the objectives I provide and leave unknown targets pending.” |
| Adjust a plan | “Adjust the reaction time in version 2 of NEW01's plan. Keep the other conditions unchanged.” |
| Calculate a formulation | “For NEW01, calculate A:B ratios of 1:1, 1:2, and 1:3, with 30 g per group and two independent replicates per condition. Export a formulation workbook.” |
| Confirm batch completion | “The first two groups of that batch were completed today according to the formulation. Actual weighed quantities and results will follow. Add them to the daily record.” |
| Add daily records | “Record the actual material additions and test results for today's NEW01 samples, referencing the plan version we just used.” |
| Query a sample | “Find all experiment records and plan versions for NEW01-20300107-1.” |
| Create a weekly report | “Create a weekly PowerPoint from NEW01's daily records for this week. Preserve sample and test-step details.” |
| Create a monthly report | “Summarize NEW01's work this month in Excel using the blank monthly report template.” |

These project IDs, sample IDs, and ratios are usage examples. Use your own projects and experimental conditions for actual work. The general project template is [templates/project-context.yaml](templates/project-context.yaml); it can store user-confirmed objectives, stages, and project consolidation rules.

### From formulation batches to daily records

1. Describe the materials, calculation basis, total quantity, gradients, and number of replicates. The assistant previews the calculations and lists parameter sources and missing inputs. Multiple gradients can expand as paired values or all combinations; clarify ambiguous intent first.
2. Save a batch revision linked to a fixed plan version. Independent replicates can share a plan snapshot, while each group retains its own experiment-group ID.
3. Export an Excel workbook with the “配方总览” (Formulation overview) and “参数与计算” (Parameters and calculations) sheets. Verify the formulas and render both sheets for inspection.
4. After the user confirms completion of the whole batch or selected groups, write daily records using the actual experiment dates. Link the samples, plan version, batch revision, and experiment groups. Record work completed on different dates separately.
5. Add actual weighed quantities, deviations from planned conditions, and test results. Preserve the original record ID when correcting an existing fact. Repeated confirmations and interrupted-operation retries retain existing record links.

Saving a formulation does not create samples or daily records. Planned quantities and actual measurements are recorded separately; unreported results remain pending. Excel is an export of the selected batch revision. After editing cells, ask the assistant to recalculate and save a new revision to update the batch data. Save a new export separately if an existing export has manual edits.

### Record and version rules

- Daily Word records store experimental facts. Context YAML, plan JSON, and batch JSON retain their respective versions and links.
- The user must explicitly select the best plan. Creating a plan or completing a batch does not change that designation automatically.
- Record what is known and leave missing information pending. Label planned, calculated, and actually measured values separately.
- Keep sample, branch, step, and record IDs stable to support traceability across dates and index rebuilding.

## Fictional demonstration

All data in `examples/` are **fictional software examples and must not be used as experimental conditions or real results**. They are imported only when you explicitly run:

```sh
<installed-python> <program-dir>/scripts/demo.py --root /path/to/empty-demo-data
```

The demonstration requires empty context, plan, and report subdirectories in the target directory. It generates a project, a plan, two linked daily records, a sample tracking document, a plan overview, and monthly summary JSON. It does not select a best plan automatically. Then ask Codex to create and render a weekly PowerPoint and monthly Excel report using that demonstration directory. Keep demonstration data separate from real data.

## Data and configuration

Program templates live in the installed package. The data directory contains:

```text
references/                  Project YAML and version history
plans/                       Plan snapshots and exports
plans/PROJECT/STAGE/batches/  Formulation batch revisions, exports, and operation logs
report/YYYY-MM/              Daily records, tracking documents, final weekly/monthly reports
report/index.json            Rebuildable index
work/                        Candidate plans, temporary summaries, and rendering checks
```

Data directory precedence is: command-line `--root` → `LAB_RD_DATA_ROOT` → legacy variable `REPORT_SKILLS_ROOT` → `data_dir` in the installation's `local.json` → `~/.lab-rd/data`. Legacy environment variables override installation settings, so check them when switching data directories. Template paths always use the program directory and do not change with the data directory.

Day-to-day commands retain the `--root` interface:

```sh
<installed-python> <program-dir>/scripts/lab_records.py --root /path/to/data query --sample NEW01-20300107-1
<installed-python> <program-dir>/scripts/lab_plans.py --root /path/to/data list --project NEW01
<installed-python> <program-dir>/scripts/lab_formulations.py --root /path/to/data list --project NEW01
```

`<installed-python>` and `<program-dir>` are explanatory placeholders. Replace them with actual paths before running the commands. JSON inputs use UTF-8, and `--root` goes before the subcommand. For everyday use, you can ask Codex to run these tools directly.

## Upgrades, migration, and backups

After pulling the latest repository version, run the installer again. Omitting `--data-dir` preserves the existing configuration. Before an upgrade, managed program files and configuration are backed up to `.lab-rd-backups/` beside the skills directory. User-added files in the program directory are preserved. A failed installation does not disable the five legacy skill entries.

When migrating from the legacy system, explicitly select the original data root:

```sh
python3 scripts/install.py --data-dir /path/to/old-data --retire-legacy
```

After core checks pass, the five legacy skills are moved into the backup directory with their customizations intact. This option does not scan or rewrite daily records, renumber samples, or move experimental data. You can omit it initially and run it after checking the new skill entry.

To move to another computer, copy the **entire data directory**, install the program on the new machine, and point it at that directory. Program and data directories can move independently. After moving the program, reinstall it at the new location to rebuild its virtual environment. Back up real experimental data separately; Git is not the data backup system.

Daily Word records are the source of experimental facts. Plan JSON and context YAML retain versions. Rebuild a lost index with:

```sh
<installed-python> <program-dir>/scripts/lab_records.py --root /path/to/data rebuild
```

Register historical monthly Word documents explicitly as authoritative sources with `--legacy <relative-path>`; do not automatically merge all old snapshots. If a batch write is interrupted, retry using the original operation ID and exactly the same input. Preserve operation logs for recovery.

## Repository layout and developer documentation

```text
skills/lab-rd/         Skill entry and workflow modules
scripts/              Installation, records, plans, formulation calculations, and exports
templates/            Blank project and monthly report templates
examples/             Fictional demonstration data
tests/                Installation and portability tests
.github/workflows/    Automated tests on three operating systems
README.md             Chinese installation and usage guide
README.en.md          English installation and usage guide
VALIDATION.md         Validation records and known limitations
```

| Document | Contents |
| --- | --- |
| [Skill entry](skills/lab-rd/SKILL.md) | Module selection, program and data paths, and report runtime requirements |
| [Formulation batch contract](scripts/lab_formulations_contract.md) | Calculation modes, gradients, revisions, completion confirmation, and retries |
| [Experiment plan contract](scripts/lab_plans_contract.md) | Plan snapshots, condition inheritance, and best-plan designation |
| [Experiment record contract](scripts/lab_records_contract.md) | Daily record fields, sample IDs, links, and corrections |
| [Research workflow contract](scripts/research_workflow_contract.md) | Sources for quantities and material properties, literature suggestions, and technical routes |

The linked workflow contracts and skill documents are primarily in Chinese.

## Development and platform validation

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python tests/run_tests.py
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.lock
& ./.venv/Scripts/python.exe tests/run_tests.py
```

The shared test entry point stores temporary data in `work/test-temp/`. Tests cover records, plans, research workflows, formulation arithmetic, batch lifecycles, installation from a clean copy, repeated installation, upgrades, Chinese paths, data isolation, and missing dependencies.

The [GitHub Actions workflow](.github/workflows/test.yml) runs nine combinations of Windows, macOS, and Linux with Python 3.12, 3.13, and 3.14, including core tests and separate installation checks.

See [VALIDATION.md](VALIDATION.md) for validation records across the three operating systems. Check the repository's [Actions page](https://github.com/dancingash/chemistry-lab-assistant/actions) for each new commit's results. Local formulation-batch tests and report QA are also recorded in the validation document. Full reporting uses Codex's dedicated runtime and requires a complete environment check and sample report rendering on the target machine. Standard CI validates the core tools and installation.

## Recent updates

- Added a formulation calculation engine, gradient and replicate expansion, recoverable batch revisions, and a completion workflow that writes daily records.
- Added two-sheet formulation workbook exports, with numerical comparisons, recalculation checks after input changes, and sheet preview verification.
- Preserved batch IDs, revisions, and experiment-group links in daily queries and rebuilt indexes.
- Packaged the new modules and added regression checks for formulation and batch-completion workflows after removing access to the source checkout.
- Added linked Chinese and English guides for installation, usage, data management, and development.

The repository publishes only program files, clean templates, and fictional examples. Real projects, historical reports, runtimes, indexes, and machine-specific configuration are excluded by `.gitignore`. Install the project through `scripts/install.py`. `pyproject.toml` declares dependency metadata; `pip install .` is not a complete skill installation.
