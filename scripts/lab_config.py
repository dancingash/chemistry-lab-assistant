"""Shared portable paths. Program assets and experimental data are separate."""
import json
import os
from pathlib import Path

PROGRAM_ROOT = Path(__file__).resolve().parents[1]


def config_path():
    # Installed packages have a per-install config; development defaults are per-user.
    return PROGRAM_ROOT / 'local.json' if (PROGRAM_ROOT / 'installation.json').exists() else Path.home() / '.lab-rd' / 'config.json'


def read_config():
    path = config_path()
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def data_root(explicit=None):
    value = explicit or os.environ.get('LAB_RD_DATA_ROOT') or os.environ.get('REPORT_SKILLS_ROOT') or read_config().get('data_dir') or Path.home() / '.lab-rd' / 'data'
    return Path(value).expanduser().resolve()


def python_executable(package=PROGRAM_ROOT):
    return Path(package) / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def init_data(root):
    root = Path(root)
    for name in ('references', 'plans', 'report', 'work'):
        (root / name).mkdir(parents=True, exist_ok=True)
