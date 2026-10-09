"""Run a Node helper against the runtime supplied by Codex's dependency loader."""
import argparse
import os
from pathlib import Path
import subprocess
from lab_config import PROGRAM_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', required=True, type=Path)
    parser.add_argument('--node-modules', required=True, type=Path)
    parser.add_argument('script', choices=['build_monthly_report.mjs', 'render_lab_plan_docx.mjs'])
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    env = dict(os.environ, LAB_RD_NODE_MODULES=str(args.node_modules.resolve()))
    return subprocess.call([str(args.node), '--experimental-loader', (PROGRAM_ROOT / 'scripts/node_loader.mjs').as_uri(),
                            str(PROGRAM_ROOT / 'scripts' / args.script), *args.args], env=env)


if __name__ == '__main__':
    raise SystemExit(main())
