"""Run an installed package with its own environment, independent of the checkout."""
import json
from pathlib import Path
import subprocess
import sys

def main():
    package = Path(sys.argv[1]).resolve()
    runtime = package / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    subprocess.run([str(runtime), str(package / 'scripts/doctor.py')], check=True)
    demo = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else package.parent.parent / 'isolated fictional demo'
    subprocess.run([str(runtime), str(package / 'scripts/demo.py'), '--root', str(demo)], check=True)
    result = subprocess.run([str(runtime), str(package / 'scripts/lab_records.py'), '--root', str(demo),
                             'query', '--sample', 'DEMO-20300107-1'], check=True, capture_output=True, text=True, encoding='utf-8')
    assert len(json.loads(result.stdout)['records']) == 2

if __name__ == '__main__':
    main()
