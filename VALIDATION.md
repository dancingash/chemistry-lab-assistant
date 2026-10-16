# 0.1.0 验证记录

## 2026-10-16 All workflows 全量核查与 Actions 升级

- 核查时仓库只有 `Portable core and installer` 一个工作流，共 7 条运行记录；5 条成功，2 条历史失败。其中第二条失败运行曾执行 3 次，已逐次核对任务状态并读取全部 12 个失败任务的日志。
- [运行 1](https://github.com/dancingash/chemistry-lab-assistant/actions/runs/37887262195) 的 Windows / Python 3.12、3.13、3.14 均有两项测试报错：`test_monthly_legacy_mapping_starts_on_effective_date` 和 `test_demo_links_two_days_to_one_plan_and_refuses_overwrite`。根因是月报汇总输出中文时使用 cp1252；`13218d0` 已在月报 CLI 中调用 UTF-8 控制台配置。
- [运行 2](https://github.com/dancingash/chemistry-lab-assistant/actions/runs/37887726172) 的三次执行均在 Windows 三个 Python 版本的真实安装步骤失败，日志指向 pip 的 cp1252 编码；`00966eb` 已通过 UTF-8 管道转发修复。重新运行旧提交仍会使用旧代码。
- 其余 5 条成功运行的 45 个任务均已核对为成功；`00966eb` 的[完整矩阵](https://github.com/dancingash/chemistry-lab-assistant/actions/runs/38846711143)包含每组 76 项测试及真实隔离安装检查。
- 成功运行中仍有旧 Actions 引起的 Node.js 20 强制迁移警告及 `punycode` 弃用警告。本次将 `actions/checkout` 从 v4 升至 v7.0.1、`actions/setup-python` 从 v5 升至 v7.0.0；两者原生使用 Node.js 24。已核对官方发行说明及 action.yml，现有 GitHub 托管 runner 2.337.0 满足最低版本要求。本次升级后的任务结果与日志以新提交触发的运行记录为准。

## 2026-10-16 GitHub Actions 失败记录复核

- 当前远端 `main` 提交 `43131349774a56d7c90c2bf80efdf5bae25564aa` 的[最近一次运行](https://github.com/dancingash/chemistry-lab-assistant/actions/runs/38680775371)中，三平台 × Python 3.12、3.13、3.14 共 9 组全部通过。
- 两次历史失败分别出现在中文月报输出和真实隔离安装的 pip 输出，均涉及 Windows cp1252 无法编码中文。月报输出已有 UTF-8 修复；本次提交进一步通过管道转发 pip 日志，并增加真实 pip 离线回归及非 UTF-8 父进程下的安装检查。
- 本次重新执行原有 74 项回归及两项真实 pip 离线回归，全部通过（分两个解释器执行）；2026-10-15 条目所记录的真实安装与安装后检查同样通过。本次提交发布后的三平台结果须以新运行记录为准。

## 2026-10-15 Windows pip 中文路径编码修复

- 安装器通过 UTF-8 管道合并并逐行转发 pip 的标准输出与错误输出，保留失败退出码；禁用 pip 彩色输出和进度条。
- CI 的真实隔离安装步骤显式设置 `PYTHONIOENCODING=cp1252`、`PYTHONUTF8=0`、`PYTHONLEGACYWINDOWSSTDIO=1`，继续使用中文和空格路径。
- Windows / Python 3.13.1 / pip 25.3：两项新增离线测试通过，覆盖真实 `pip --python` 向不含 pip 的虚拟环境安装本地 wheel，以及失败时保留中文诊断和退出码。
- Windows / Python 3.12.14：原有 74 项回归测试通过；该解释器不含 pip，两项新增测试在此轮跳过，已由上述 Python 3.13 单独验证。
- Windows / Python 3.13.1：在上述 cp1252 环境和中文、空格路径中完成真实隔离安装，9 个固定依赖全部安装成功；新环境通过 `tests/check_installed.py` 的核心能力检查、演示生成和样品查询。此次仅验证核心功能，不包含专用报告引擎和视觉 QA。
- Python 语法、工作流 YAML 配置及 `git diff --check` 检查通过。本次修复尚未重跑 GitHub Actions 三平台矩阵或验证 Python 3.14。

## 2026-10-15 发布前检查

- 使用已安装的独立 Python 环境执行 `tests/run_tests.py`，74 项回归测试全部通过。
- 新增配方 Excel 导出脚本通过 `node --check`；`git diff --check` 通过。
- 中文 README 的 9 个 Markdown 链接已检查，仓库内链接均指向现有文件。
- 本次检查未重新渲染报告，未验证新提交的三平台 GitHub Actions 结果；报告 QA 与历史 CI 的范围见下文。

## 2026-10-14 配方批次功能

- Windows 本地完整回归 74 项通过，包括 26 项新增配方算术和批次生命周期测试。
- 覆盖质量比、质量分数、干湿固含量、有效成分、摩尔比、官能度/当量质量、稀释、倍数/目标总质量缩放、补足溶剂、零添加、缺失依据及冲突约束。
- 覆盖梯度展开、独立重复、版本精度、部分/跨日完成、实际偏差、重复确认、方案/日报中断重试、跨批次样品编号预留、Word 冷重建和手动内容保护。
- 干净发行副本在移走源码后，可以独立运行配方保存和完成入日报；安装与升级回归继续通过。
- 虚构批次的双工作表 Excel 通过 20 项计算结果比较、输入改动重算及还原、公式错误扫描和全部工作表预览检查。
- 虚构日报、追踪表、方案总览通过现有备用引擎预览；该引擎不呈现嵌套用量表，已另行提取表格渲染，并核对 Word 内结构化数据与可见表内容。默认渲染器因缺少 LibreOffice 不可用，未验证原生 Word/Excel 排版或执行。
- 技能 frontmatter、Python 编译、Node 语法、差异空白检查及完整报告环境检查通过。此记录不表示新版已完成三平台 CI。

验证日期：2026-10-09。

## 已执行

- Windows / Python 3.12：39 项原有记录、方案和研究流程回归测试通过；9 项新增安装、路径、恢复和演示测试通过。
- 真实安装使用独立虚拟环境及 `requirements.lock`，验证中文与空格路径、重复安装和升级。
- 从仅含发行所需文件的隔离副本安装，移走原副本后仍可运行查询；配置和数据目录独立于程序目录。
- 验证升级保留原始数据、本机配置、用户新增文件和修改过的技能备份；验证依赖安装失败可重试且旧技能不被停用。
- 虚构 DEMO：项目、方案、两天日报、同一样品查询、追踪表、方案总览、月报 JSON 的链路通过；未自动指定最优方案。
- 四份示例 Word 使用 Codex 文档引擎备用渲染器，四页均已视觉检查。默认 LibreOffice 渲染器因本机未安装 LibreOffice 无法运行。
- 示例周报三页：PPTX 包结构、页面布局、原生可编辑表格检查通过，三页预览均已视觉检查。
- 示例月报 Excel：完成导出、内容核对、公式错误扫描与预览检查；空白发布模板也已视觉检查。
- 本机完整报告环境检查通过：Python 工具、三个支持技能、Codex Node 文档/表格/演示模块和 Canvas 均可用。
- 新技能 frontmatter 验证和 Python 编译检查通过；发布文件清单排除了真实数据、旧模板、索引、工作产物和本机依赖。
- 对已有 156 个背景、方案、报告及原模板文件做 SHA256 核对，未发生内容改动。

## 三平台 CI

提交 `dfc837f5ad4069556c175d8c949c6ae89f524ea3` 的 [GitHub Actions 运行](https://github.com/dancingash/chemistry-lab-assistant/actions/runs/37888173259) 全部成功：Windows、macOS、Linux × Python 3.12、3.13、3.14，共 9 组。每组执行 48 项行为与安装测试，再从干净 checkout 在中文和空格路径中真实安装固定依赖，使用安装包自己的虚拟环境检查并运行虚构实验演示。

首次 CI 发现 Windows 英文区域设置的输出编码问题，修复了命令行工具和 pip 子进程的 UTF-8 输出；本地也完成了 `PYTHONIOENCODING=cp1252` 下的中文路径安装与演示检查。

## 仍需目标机器验证的能力

普通 CI 不包含 Codex 的专用文档引擎。其他使用者须运行 `doctor.py --require-full`，并渲染检查自己的示例产物。现有检查不能证明 Microsoft Word、PowerPoint、Excel 中的原生执行结果，也不能保证任意长记录均无需排版调整。
