# Chemistry Lab Assistant · 研发助手

一个供 Codex 使用的材料研发技能入口，统一管理项目背景、实验方案、日报、样品追溯、周报 PPT 和月报 Excel。发行包含完整脚本和空白模板，安装后可移走克隆目录。真实数据保存在使用者自己的目录中。

## 安装

准备 Python **3.12–3.14**、带技能支持的 Codex，以及联网下载 Python 依赖的环境。安装器不需要管理员权限。第一次安装下载 `requirements.lock` 中的固定依赖，创建独立虚拟环境，不修改系统 Python 包。

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

默认技能位置：`$CODEX_HOME/skills/lab-rd`；未设置 `CODEX_HOME` 时为 `~/.codex/skills/lab-rd`。默认数据位置：`~/.lab-rd/data`。安装器创建空目录，不导入示例。可以自行指定：

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

## 首次使用和五类请求

直接用自然语言指定 `$lab-rd`，也允许自动选择技能：

- 项目背景：“建立一个新研发项目 NEW01，先记录我给出的目标，未知指标保持待补。”
- 实验方案：“根据 NEW01 的现有方案调整反应时间，其余条件不变。”
- 实验日报：“记录今天 NEW01 样品的实际投料和测试结果，引用刚才的方案版本。”
- 每周汇报：“根据 NEW01 本周的日报制作周报 PPT，保留样品和测试步骤。”
- 每月汇报：“汇总 NEW01 本月工作，使用空白月报模板生成 Excel。”

入口按需读取五个模块。先创建项目，再根据实际条件建立方案；最优方案必须由使用者明确指定。简短输入可以直接记录，缺失数据保留待补。方案参数、计算值和未报告的实际测量不能混为实验事实。

通用项目模板在 `templates/project-context.yaml`，没有预设验收阈值。需要目标、阶段或项目归并规则时，将确认内容放入自己的项目 YAML。

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
report/YYYY-MM/               日报、追踪表、正式周报/月报
report/index.json             可重建索引
work/                        候选方案、临时汇总、渲染检查
```

数据目录优先级：命令 `--root` → `LAB_RD_DATA_ROOT` → 兼容变量 `REPORT_SKILLS_ROOT` → 安装目录 `local.json` 中的 `data_dir` → `~/.lab-rd/data`。旧环境变量会覆盖安装配置，切换数据目录时检查它们。模板路径始终使用程序目录，不随数据目录改变。

日常命令保留 `--root` 接口，例如：

```sh
<安装的Python> <程序目录>/scripts/lab_records.py --root /path/to/data query --sample NEW01-20300107-1
<安装的Python> <程序目录>/scripts/lab_plans.py --root /path/to/data list --project NEW01
```

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

历史月度 Word 需要以 `--legacy <相对路径>` 显式登记权威源，不能自动混入所有旧快照。数据契约详见 `scripts/*_contract.md`。

## 开发与平台验证

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m unittest discover -s scripts -p 'test_lab_*.py'
.venv/bin/python -m unittest discover -s tests
```

Windows 用 `.venv/Scripts/python.exe`。`.github/workflows/test.yml` 配置 Windows、macOS、Linux 和 Python 3.12/3.13/3.14 的核心测试，包括干净副本安装、重复安装、升级、中文路径、数据隔离与缺失依赖。

Windows、macOS、Linux × Python 3.12/3.13/3.14 的 9 组核心测试与独立安装检查已通过 [GitHub Actions](https://github.com/dancingash/chemistry-lab-assistant/actions/runs/37888173259)。平台与报告 QA 记录见 [VALIDATION.md](VALIDATION.md)。完整报告使用 Codex 专用运行环境，需要在目标机器执行完整环境检查及示例报告渲染；普通 CI 验证核心工具和安装，不宣称完成 Codex 图形引擎验证。

仓库仅发布程序、干净模板和虚构示例。真实项目、历史报告、运行库、索引和本机配置均被 `.gitignore` 排除。本项目的安装入口是 `scripts/install.py`，`pyproject.toml` 声明依赖元数据，不将 `pip install .` 作为完整技能安装。
