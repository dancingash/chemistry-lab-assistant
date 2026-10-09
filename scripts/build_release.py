"""Build a source ZIP from Git's public file list; never enumerate private workspace data."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def build(output, git='git'):
    result = subprocess.run([git, '-c', 'core.quotepath=false', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                            cwd=ROOT, capture_output=True, check=True)
    files = sorted(set(result.stdout.decode('utf-8').strip('\0').split('\0')) - {''})
    required = {'scripts/install.py', 'skills/lab-rd/SKILL.md', 'templates/monthly-summary.xlsx', 'requirements.lock', 'README.md'}
    if not required.issubset(files):
        raise ValueError('Incomplete Git source list')
    allowed_directories = {'scripts', 'skills', 'templates', 'tests', 'examples', '.github'}
    allowed_roots = {'.gitignore', '.gitattributes', 'README.md', 'VALIDATION.md', 'package.json', 'pyproject.toml', 'requirements.lock'}
    for relative in files:
        parts = Path(relative).parts
        if parts[0] not in allowed_directories and relative not in allowed_roots:
            raise ValueError('Unexpected release file: ' + relative)
        if parts[0] == 'skills' and not relative.startswith('skills/lab-rd/'):
            raise ValueError('Unexpected skill: ' + relative)
        if parts[0] == 'templates' and relative not in ('templates/monthly-summary.xlsx', 'templates/project-context.yaml'):
            raise ValueError('Unexpected template: ' + relative)
        if not (ROOT / relative).resolve().is_relative_to(ROOT) or (ROOT / relative).is_symlink():
            raise ValueError('Release must contain regular in-repository files: ' + relative)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError('Output exists; choose a new release filename')
    with ZipFile(output, 'x', ZIP_DEFLATED) as archive:
        for relative in files:
            archive.write(ROOT / relative, 'lab-rd-0.1.0/' + relative)
    return {'output': str(output), 'files': len(files), 'contains_data': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/lab-rd-0.1.0-source.zip')
    parser.add_argument('--git', default='git')
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.git), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
