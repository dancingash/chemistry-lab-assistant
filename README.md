# Chemistry Lab Assistant · 材料研发助手

面向 Codex 的中文材料研发工作流，通过一个 `$lab-rd` 技能入口管理项目背景、版本化实验方案、配方批次、实验日报与样品追溯，并生成 Word、周报 PowerPoint 和月报 Excel。

你可以直接描述研发任务，由助手调用相应模块完成记录、计算和导出。程序、模板与实验数据分开保存，安装后可以移走仓库克隆目录。

## 功能概览

| 功能 | 主要能力 | 数据或输出 |
| --- | --- | --- |
| 项目背景 | 维护目标、阶段、技术路线与背景版本 | 项目 YAML、版本历史 |
| 实验方案 | 调整条件、继承指定版本、记录使用者指定的最优方案 | 方案 JSON、Word 方案总览与 SOP |
| 配方与批次 | 计算用量、展开梯度和独立重复、保存批次修订 | 批次 JSON、双工作表配方 Excel |
| 实验日报 | 记录实际操作、用量、测试结果与待补信息 | 日报 Word、样品追踪表 |
| 样品追溯 | 关联样品、分支、步骤、方案版本与配方实验组 | 可重建索引、跨日期查询 |
| 周报与月报 | 汇总已记录的工作，保留样品和测试步骤 | 周报 PPT、月报 Excel |

配方模块支持质量比、质量分数、干湿基固含量、有效成分换算、摩尔比、当量、浓度稀释、配方缩放及按质量补足溶剂。所需物性参数保留来源，缺失参数标为待补。

## 快速安装

准备 Python **3.12–3.14**、带技能支持的 Codex，以及联网下载 Python 依赖的环境。支持 Windows、macOS 和 Linux。安装器不需要管理员权限；第一次安装下载 `requirements.lock` 中的固定依赖，创建独立虚拟环境。

克隆仓库并进入其根目录（私有仓库需要先配置 GitHub 访问权限）：

```sh
git clone https://github.com/dancingash/chemistry-lab-assistant.git
cd chemistry-lab-assistant
```

然后执行安装：

Windows PowerShell：

```powershell
py -3.12 scripts/install.py
```

macOS / Linux：

```sh
python3 scripts/install.py
```

默认技能位置：`$CODEX_HOME/skills/lab-rd`；未设置 `CODEX_HOME` 时为 `~/.codex/skills/lab-rd`。默认数据位置：`~/.lab-rd/data`。安装器创建空目录，不导入示例。可以自行指定安装和数据目录：

```sh
python3 scripts/install.py --skills-dir /path/to/codex/skills --data-dir /path/to/research-data
```

Windows 用 `py -3.12` 替换 `python3`，路径有空格时加引号。重新打开 Codex 的技能发现界面，确认出现“研发助手”；若当前聊天仍显示旧列表，开启新聊天。

安装后的程序目录下含 `SKILL.md`、`scripts/`、`templates/`、`examples/`、`.venv/`、`local.json` 和安装清单。它们不再引用克隆目录。以下命令中的 `<程序目录>` 指安装后的 `lab-rd` 目录。

## 环境检查和报告能力

Windows：

```powershell
& "$env:USERPROFILE/.codex/skills/lab-rd/.venv/Scripts/python.exe" "$env:USERPROFILE/.codex/skills/lab-rd/scripts/doctor.py"
```

macOS / Linux：

```sh
~/.codex/skills/lab-rd/.venv/bin/python ~/.codex/skills/lab-rd/scripts/doctor.py
```

自定义安装目录或 `CODEX_HOME` 的使用者替换对应路径。`core_ready` 表示 Python 工具和模板可用；`full_report_ready` 还要求三个支持技能及 Codex 的 Node 文档引擎可用。只具备核心能力时可以维护背景、方案和日报数据；不能因此宣称完整报告环境已就绪。

完整报告需要 **Documents、Presentations、Spreadsheets** 支持技能。缺少时通过 Codex 的技能/插件管理安装相应能力；本项目不复制这些插件。请在 Codex 中输入：

> 使用 $lab-rd 检查完整报告环境。调用 load_workspace_dependencies，将实际 Node 路径、Node 包目录，以及三个支持技能的 SKILL.md 路径传给 doctor.py --require-full。

对应检查接口：

```sh
<安装的Python> <程序目录>/scripts/doctor.py --require-full \
  --node <实际Node路径> --node-modules <实际Node包目录> \
  --documents-skill <Documents的SKILL.md> \
  --presentations-skill <Presentations的SKILL.md> \
  --spreadsheets-skill <Spreadsheets的SKILL.md>
```

环境检查不会写入实验数据，也不能替代每份产物的渲染与视觉检查。Word 默认使用 Documents 的渲染器；其不可用时，方案模块提供 Codex 文档引擎的替代渲染路径。PPT 由 Presentations 负责制作与核验，Excel 由 Spreadsheets 负责制作与核验。字体和渲染器缺失必须明确报告。

## 使用流程

建议按“建立项目 → 制定方案或配方 → 执行实验并记录 → 查询追溯 → 生成汇报”的顺序开始。已有项目可直接继续相应步骤。

直接用自然语言指定 `$lab-rd`，也允许自动选择技能：

| 场景 | 对话示例 |
| --- | --- |
| 建立项目 | “使用 $lab-rd 建立研发项目 NEW01，先记录我给出的目标，未知指标保持待补。” |
| 调整方案 | “根据 NEW01 的第 2 版方案调整反应时间，其余条件不变。” |
| 计算配方 | “计算 NEW01 中 A:B 为 1:1、1:2、1:3，每组总量 30 g，各独立重复两次，输出配方 Excel。” |
| 确认批次完成 | “刚才这批的前两组今天已完成，按配方执行，实际称量和结果稍后补充，加入日报。” |
| 补充日报 | “记录今天 NEW01 样品的实际投料和测试结果，引用刚才的方案版本。” |
| 查询样品 | “查询 NEW01-20300107-1 的全部实验记录和使用的方案版本。” |
| 制作周报 | “根据 NEW01 本周的日报制作周报 PPT，保留样品和测试步骤。” |
| 制作月报 | “汇总 NEW01 本月工作，使用空白月报模板生成 Excel。” |

以上项目编号、样品编号和配比均为使用示例。实际工作中使用自己的项目与实验条件。通用项目模板位于 [templates/project-context.yaml](templates/project-context.yaml)，可记录使用者确认的目标、阶段或项目归并规则。

### 配方批次如何进入实验日报

1. 描述原料、计算基准、总量、梯度和重复次数，助手预览计算结果，列出参数来源和待补项。多个梯度可按一一对应或全组合展开，含义不明确时先核对。
2. 保存批次修订并关联固定的方案版本；独立重复可共用方案快照，每组保留自己的实验组编号。
3. 导出含“配方总览”和“参数与计算”的 Excel，核对公式并渲染检查两个工作表。
4. 使用者确认整批或指定组完成后，按实际实验日期写入日报，关联样品、方案版本、批次修订和实验组。跨日完成分别记录。
5. 补充实际称量、条件偏差和测试结果；修正已有事实时沿用原记录编号。重复确认及中断重试保留既有记录关联。

保存配方时不创建样品或日报。计划用量和实际称量分别记录，未报告的结果保持待补。Excel 是所选批次修订的导出文件，修改单元格后，需要通过对话重新计算并保存新版，才会更新批次数据。已有手动编辑的导出文件需要另存。

### 记录与版本规则

- 日报 Word 保存实验事实；背景 YAML、方案 JSON 和批次 JSON 保存各自的版本与关联。
- 最优方案由使用者明确指定。建立方案或完成批次不会自动更改最优标记。
- 已知的部分可以直接记录，缺失信息保留待补；计划值、计算值、实际测量值分别标注。
- 样品、分支、步骤和记录编号保持稳定，支持跨日期追溯及索引重建。

## 虚构演示

`examples/` 的所有数据均为**软件虚构示例，不能作为实验条件或真实结果使用**。只有显式运行以下命令才导入：

```sh
<安装的Python> <程序目录>/scripts/demo.py --root /path/to/empty-demo-data
```

演示器要求目标目录的背景、方案和报告子目录为空，生成项目、方案、两份关联日报、追踪表、方案总览和月报汇总 JSON，不自动设定最优方案。然后让 Codex 使用该演示目录制作并渲染周报 PPT 和月报 Excel。演示目录应与真实数据分开。

## 数据与配置

程序模板位于安装包；数据目录包含：

```text
references/                  项目 YAML 和版本历史
plans/                       方案快照与导出文件
plans/PROJECT/STAGE/batches/  配方批次修订、导出文件与操作日志
report/YYYY-MM/               日报、追踪表、正式周报/月报
report/index.json             可重建索引
work/                        候选方案、临时汇总、渲染检查
```

数据目录优先级：命令 `--root` → `LAB_RD_DATA_ROOT` → 兼容变量 `REPORT_SKILLS_ROOT` → 安装目录 `local.json` 中的 `data_dir` → `~/.lab-rd/data`。旧环境变量会覆盖安装配置，切换数据目录时检查它们。模板路径始终使用程序目录，不随数据目录改变。

日常命令保留 `--root` 接口，例如：

```sh
<安装的Python> <程序目录>/scripts/lab_records.py --root /path/to/data query --sample NEW01-20300107-1
<安装的Python> <程序目录>/scripts/lab_plans.py --root /path/to/data list --project NEW01
<安装的Python> <程序目录>/scripts/lab_formulations.py --root /path/to/data list --project NEW01
```

`<安装的Python>` 和 `<程序目录>` 是说明用占位符，执行前替换为实际路径。JSON 输入使用 UTF-8，命令的 `--root` 放在子命令之前。日常使用可直接让 Codex 调用这些工具。

## 升级、迁移与备份

拉取新版仓库后重新执行安装器。省略 `--data-dir` 时保留原配置。升级前将被管理的程序文件和配置备份到技能目录旁的 `.lab-rd-backups/`，程序目录中的用户新增文件也会保留。失败安装不会停用旧五个入口。

从旧系统迁移时显式指定原数据根目录：

```sh
python3 scripts/install.py --data-dir /path/to/old-data --retire-legacy
```

核心检查通过后，旧五个技能整体移入备份目录，保留自定义内容。此选项不扫描或改写日报、不重编号、不移动实验数据。首次迁移也可以省略此选项，检查新入口后再运行。

换电脑时复制**完整数据目录**，在新机器安装并指定它。程序和数据目录可独立移动；程序移动后应在新位置重新安装以重建虚拟环境。正式数据需要单独备份，Git 不承担实验数据备份。

日报 Word 是事实来源，方案 JSON 和背景 YAML 保留版本。索引丢失可重建：

```sh
<安装的Python> <程序目录>/scripts/lab_records.py --root /path/to/data rebuild
```

历史月度 Word 需要以 `--legacy <相对路径>` 显式登记权威源，不能自动混入所有旧快照。批次写入中断时，使用原操作编号和完全相同的输入重试，保留操作日志以便恢复。

## 仓库结构与开发文档

```text
skills/lab-rd/         技能入口及各工作流模块
scripts/               安装、记录、方案、配方计算和导出工具
templates/             空白项目与月报模板
examples/              虚构演示数据
tests/                 安装与可迁移性测试
.github/workflows/     三平台自动测试
README.md              中文安装与使用说明
VALIDATION.md          验证记录与已知限制
```

| 文档 | 内容 |
| --- | --- |
| [技能入口](skills/lab-rd/SKILL.md) | 模块选择、程序与数据路径、报告引擎要求 |
| [配方批次契约](scripts/lab_formulations_contract.md) | 计算模式、梯度、修订、完成确认与重试 |
| [实验方案契约](scripts/lab_plans_contract.md) | 方案快照、条件继承和最优标记 |
| [实验记录契约](scripts/lab_records_contract.md) | 日报字段、样品编号、关联和修正 |
| [研究工作流契约](scripts/research_workflow_contract.md) | 用量与物性来源、文献建议和技术路线 |

## 开发与平台验证

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python tests/run_tests.py
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.lock
& ./.venv/Scripts/python.exe tests/run_tests.py
```

统一测试入口将临时数据放入 `work/test-temp/`。测试覆盖记录、方案、研究流程、配方算术与批次生命周期，以及干净副本安装、重复安装、升级、中文路径、数据隔离与缺失依赖。

[GitHub Actions 配置](.github/workflows/test.yml) 包含 Windows、macOS、Linux × Python 3.12/3.13/3.14 的 9 组核心测试及独立安装检查。

历史提交 `dfc837f` 的 9 组检查已通过，详见 [VALIDATION.md](VALIDATION.md) 中的运行记录；新提交的检查结果请查看仓库的 [Actions 页面](https://github.com/dancingash/chemistry-lab-assistant/actions)。配方批次功能的本地测试及报告 QA 也记录在验证文档中。完整报告使用 Codex 专用运行环境，需要在目标机器执行完整环境检查及示例报告渲染；普通 CI 验证核心工具和安装。

## 本次更新

- 新增配方计算引擎、梯度与重复展开、可恢复的批次修订和完成入日报流程。
- 新增双工作表配方 Excel 导出，包含数值比对、输入变化重算和工作表预览检查。
- 日报查询和索引重建保留批次编号、修订与实验组关联。
- 安装器打包新模块，并增加脱离源码目录运行配方和批次完成的回归检查。
- 完善中文安装、使用流程、数据管理与开发文档。

仓库仅发布程序、干净模板和虚构示例。真实项目、历史报告、运行库、索引和本机配置均被 `.gitignore` 排除。本项目的安装入口是 `scripts/install.py`，`pyproject.toml` 声明依赖元数据，不将 `pip install .` 作为完整技能安装。
