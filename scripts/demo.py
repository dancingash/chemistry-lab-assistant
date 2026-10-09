"""Explicitly import fictional data. No report QA or real experimentation is implied."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from lab_config import PROGRAM_ROOT, init_data


def create_demo(root):
    root = Path(root).resolve()
    for name in ('references', 'plans', 'report'):
        if (root / name).exists() and any((root / name).iterdir()):
            raise ValueError('Demo requires empty references/plans/report directories; choose a separate directory')
    init_data(root)
    def run(script, *args):
        return subprocess.run([sys.executable, str(PROGRAM_ROOT / 'scripts' / script), '--root', str(root), *map(str, args)], check=True)
    run('project_context.py', 'update', PROGRAM_ROOT / 'examples/project.yaml', '--effective-date', '2030-01-07')
    run('lab_plans.py', 'create', PROGRAM_ROOT / 'examples/plan.json')
    records = json.loads((PROGRAM_ROOT / 'examples/records.json').read_text(encoding='utf-8'))['records']
    # The record contract saves one day at a time, preserving retry identifiers.
    for day in sorted({record['date'] for record in records}):
        payload = root / 'work' / ('demo-' + day + '.json')
        payload.write_text(json.dumps({'records': [r for r in records if r['date'] == day]}, ensure_ascii=False), encoding='utf-8')
        run('lab_records.py', 'save', payload)
    run('lab_plans.py', 'export', '--project', 'DEMO', '--stage', 'validation')
    extract = root / 'work/demo-records.json'
    run('lab_records.py', 'query', '--start', '2030-01-01', '--end', '2030-01-31', '--out', extract)
    summary = root / 'work/demo-summary.json'
    subprocess.run([sys.executable, str(PROGRAM_ROOT / 'scripts/build_monthly_summary.py'), str(extract),
                    '--references-dir', str(root / 'references'), '--month', '2030-01', '--out', str(summary)], check=True)
    return {'fictional': True, 'root': str(root), 'summary': str(summary),
            'next': 'Ask lab-rd to create and visually verify a weekly PPT and a monthly XLSX from this isolated data.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Empty isolated demonstration data directory')
    args = parser.parse_args()
    try:
        print(json.dumps(create_demo(args.root), ensure_ascii=False, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
