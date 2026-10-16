"""Install a complete lab-rd skill. No administrator rights or shell scripts required."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv

from lab_config import configure_console, PROGRAM_ROOT, init_data, python_executable

LEGACY = ('lab-daily-report', 'lab-experiment-plan', 'lab-project-context', 'lab-weekly-report', 'lab-monthly-report')
SCRIPTS = ('lab_config.py', 'lab_records.py', 'lab_plans.py', 'project_context.py',
           'lab_formulations.py', 'lab_formulation_calc.py', 'build_formulation_workbook.mjs',
           'lab_formulations_contract.md',
           'lab_quantities.py', 'lab_materials_docx.py', 'extract_daily_docx.py',
           'build_monthly_summary.py', 'build_monthly_report.mjs', 'render_lab_plan_docx.mjs',
           'node_loader.mjs', 'run_node.py', 'doctor.py', 'demo.py',
           'lab_records_contract.md', 'lab_plans_contract.md', 'research_workflow_contract.md')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_files(source):
    source = Path(source)
    files = {p.relative_to(source / 'skills/lab-rd').as_posix(): p
             for p in (source / 'skills/lab-rd').rglob('*') if p.is_file()}
    for name in SCRIPTS:
        files['scripts/' + name] = source / 'scripts' / name
    for directory in ('templates', 'examples'):
        names = ('monthly-summary.xlsx', 'project-context.yaml') if directory == 'templates' else ('project.yaml', 'plan.json', 'records.json')
        for name in names:
            files[directory + '/' + name] = source / directory / name
    files.update({name: source / name for name in ('requirements.lock', 'pyproject.toml', 'README.md', 'VALIDATION.md')})
    for relative, path in files.items():
        if not path.is_file():
            raise ValueError('Incomplete release: ' + relative)
    return files


def managed_path(target, relative):
    path = target / relative
    if not path.resolve().is_relative_to(target.resolve()) or path == target:
        raise ValueError('Unsafe managed path: ' + relative)
    return path


def install_dependencies(runtime, requirements):
    # Pipes make PYTHONIOENCODING effective even with legacy Windows console
    # handles. Reconfiguring this process's streams does not affect pip's streams.
    command = [sys.executable, '-m', 'pip', '--python', str(runtime), 'install',
               '--disable-pip-version-check', '--no-color', '--progress-bar', 'off',
               '-r', str(requirements)]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace',
                          env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}) as process:
        for line in process.stdout:
            print(line, end='', flush=True)
        returncode = process.wait()
    if returncode:
        raise subprocess.CalledProcessError(returncode, command)


def install(source, skills_dir, data_dir=None, skip_deps=False, retire_legacy=False):
    if not (3, 12) <= sys.version_info[:2] < (3, 15):
        raise ValueError('Python 3.12–3.14 is required')
    source, skills_dir = Path(source).resolve(), Path(skills_dir).expanduser().resolve()
    target = skills_dir / 'lab-rd'
    if target.is_symlink() or (hasattr(target, 'is_junction') and target.is_junction()):
        raise ValueError('Installed program directory must not be a link to another directory')
    files = package_files(source)
    config_file = target / 'local.json'
    pending_file = target / '.installation-pending.json'
    pending = json.loads(pending_file.read_text(encoding='utf-8')) if pending_file.exists() else {}
    if pending and pending.get('installer') != 'lab-rd':
        raise ValueError('Unknown pending installation; leave existing files intact')
    old_config = json.loads(config_file.read_text(encoding='utf-8')) if config_file.exists() else pending
    chosen = Path(data_dir).expanduser().resolve() if data_dir is not None else Path(old_config.get('data_dir', Path.home() / '.lab-rd/data')).expanduser().resolve()
    if chosen.is_relative_to(target) or target.is_relative_to(chosen):
        raise ValueError('Data directory must be separate from the installed program directory')
    receipt_file = target / 'installation.json'
    if target.exists() and any(target.iterdir()) and not receipt_file.exists() and not pending_file.exists():
        raise ValueError('Unmanaged lab-rd directory exists; choose another skills directory or move it aside')
    if not skip_deps and importlib.util.find_spec('pip') is None:
        raise ValueError('The installer Python needs pip. Run python -m ensurepip --upgrade or install Python with pip enabled.')
    old = json.loads(receipt_file.read_text(encoding='utf-8')) if receipt_file.exists() else {}
    target.mkdir(parents=True, exist_ok=True)
    lock_path = target / '.install-lock'
    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        pending_file.write_text(json.dumps({'installer': 'lab-rd', 'data_dir': str(chosen)}), encoding='utf-8')
        with tempfile.TemporaryDirectory(prefix='.lab-rd-stage-', dir=skills_dir) as temporary:
            stage = Path(temporary)
            for relative, path in files.items():
                destination = stage / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
            runtime = python_executable(target)
            dependency_hash = sha(stage / 'requirements.lock')
            if not skip_deps:
                if not runtime.exists():
                    venv.EnvBuilder(with_pip=False).create(target / '.venv')
                if old.get('dependency_hash') != dependency_hash:
                    # Also supports Codex's embedded Python, which has pip but no ensurepip wheels.
                    install_dependencies(runtime, stage / 'requirements.lock')
                subprocess.run([str(runtime), '-c', 'import docx, yaml, openpyxl, pptx'], check=True)
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = skills_dir.parent / '.lab-rd-backups' / timestamp
            # Preserve changed managed files, configuration and user additions before upgrade.
            if old:
                backup.mkdir(parents=True)
                for relative in old.get('files', {}):
                    path = managed_path(target, relative)
                    if path.is_file():
                        destination = backup / 'lab-rd' / relative
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(path, destination)
                for name in ('local.json', 'installation.json'):
                    shutil.copy2(target / name, backup / name)
            for relative in old.get('files', {}):
                if relative not in files:
                    path = managed_path(target, relative)
                    if path.is_file():
                        path.unlink()
            for relative in files:
                destination = managed_path(target, relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Replace individual files atomically; unknown user files remain untouched.
                replacement = destination.with_name(destination.name + '.install-new')
                shutil.copy2(stage / relative, replacement)
                os.replace(replacement, destination)
            config = dict(old_config, data_dir=str(chosen))
            config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
            receipt = {'version': '0.1.0', 'files': {r: sha(target / r) for r in files},
                       'dependency_hash': dependency_hash if not skip_deps else old.get('dependency_hash'),
                       'installed_at': timestamp}
            receipt_file.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            init_data(chosen)
            if retire_legacy:
                subprocess.run([str(runtime if not skip_deps else sys.executable), str(target / 'scripts/doctor.py')], check=True)
                for name in LEGACY:
                    previous = skills_dir / name
                    if previous.exists():
                        if previous.is_symlink() or not previous.resolve().is_relative_to(skills_dir):
                            raise ValueError('Legacy skill points outside skills directory: ' + name)
                        backup.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(previous), str(backup / name))
            pending_file.unlink(missing_ok=True)
            return {'installed': str(target), 'data_dir': str(chosen),
                    'python': str(runtime), 'backup': str(backup) if backup.exists() else None,
                    'core_dependencies_installed': not skip_deps}
    finally:
        lock_path.unlink(missing_ok=True)


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=PROGRAM_ROOT)
    parser.add_argument('--skills-dir', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'skills')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--retire-legacy', action='store_true', help='Back up and disable the five previous lab skills after core validation')
    parser.add_argument('--skip-deps', action='store_true', help='Packaging tests/offline preparation only; does not make the installation ready')
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.source, args.skills_dir, args.data_dir, args.skip_deps, args.retire_legacy), ensure_ascii=False, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('Installation failed: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
