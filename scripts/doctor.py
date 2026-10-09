"""Read-only checks. Full report readiness needs both tools and supporting skills."""
import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from lab_config import configure_console, PROGRAM_ROOT, data_root, python_executable


def check(node=None, node_modules=None, skills=None):
    issues = []
    core = (3, 12) <= sys.version_info[:2] < (3, 15)
    if not core:
        issues.append('Install Python 3.12–3.14 and rerun the installer.')
    for name in ('docx', 'yaml', 'openpyxl', 'pptx'):
        try:
            importlib.import_module(name)
        except ImportError:
            core = False
            issues.append('Missing ' + name + ': rerun scripts/install.py without --skip-deps.')
    assets = all((PROGRAM_ROOT / 'templates' / n).is_file() for n in ('monthly-summary.xlsx', 'project-context.yaml'))
    core = core and assets
    if not assets:
        issues.append('Incomplete templates: reinstall from a complete release.')
    installed = (PROGRAM_ROOT / 'installation.json').exists()
    if installed and (not python_executable().is_file() or Path(sys.prefix).resolve() != (PROGRAM_ROOT / '.venv').resolve()):
        core = False
        issues.append('Use the installed .venv Python; an offline package is not a ready installation.')
    supporting = {}
    for name in ('documents', 'presentations', 'spreadsheets'):
        value = (skills or {}).get(name)
        p = Path(value) if value else None
        supporting[name] = bool(p and p.is_file() and 'description:' in p.read_text(encoding='utf-8-sig'))
        if not supporting[name]:
            issues.append('Enable the ' + name + ' supporting skill and supply its SKILL.md path to doctor.')
    node_ok = False
    if node and node_modules:
        try:
            env = dict(os.environ, LAB_RD_NODE_MODULES=str(Path(node_modules).resolve()))
            result = subprocess.run([str(node), '--experimental-loader', (PROGRAM_ROOT / 'scripts/node_loader.mjs').as_uri(),
                '--input-type=module', '-e', "import {DocumentFile,SpreadsheetFile,FileBlob,Presentation,PresentationFile} from '@oai/artifact-tool'; import {createRequire} from 'node:module'; const {Canvas}=createRequire(import.meta.resolve('@oai/artifact-tool'))('skia-canvas'); if(!DocumentFile||!SpreadsheetFile||!FileBlob||!Presentation||!PresentationFile||!Canvas)process.exit(1)"],
                env=env, capture_output=True, text=True, timeout=45)
            node_ok = result.returncode == 0
            if not node_ok:
                issues.append('Codex Node package probe failed: ' + result.stderr[-800:])
        except (OSError, subprocess.TimeoutExpired) as exc:
            issues.append('Codex runtime unavailable: ' + str(exc))
    else:
        issues.append('Ask Codex to call load_workspace_dependencies and supply --node and --node-modules; do not guess cache paths.')
    return {'core_ready': core, 'full_report_ready': core and node_ok and all(supporting.values()),
            'supporting_skills': supporting, 'codex_runtime_ready': node_ok,
            'data_dir': str(data_root()), 'issues': issues,
            'note': 'Readiness is an environment probe. Every generated document still requires render and visual inspection.'}


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', type=Path)
    parser.add_argument('--node-modules', type=Path)
    for name in ('documents', 'presentations', 'spreadsheets'):
        parser.add_argument('--' + name + '-skill', type=Path)
    parser.add_argument('--require-full', action='store_true')
    args = parser.parse_args()
    result = check(args.node, args.node_modules, {n: getattr(args, n + '_skill') for n in ('documents', 'presentations', 'spreadsheets')})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['full_report_ready' if args.require_full else 'core_ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
