"""Run all regressions in a writable, isolated workspace temp directory."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
temporary = ROOT / 'work/test-temp'
temporary.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(temporary.resolve())
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
loader = unittest.TestLoader()
suite = unittest.TestSuite([loader.discover(str(ROOT/'scripts'), pattern='test_lab_*.py'),
                           unittest.TestLoader().discover(str(ROOT/'tests'), pattern='test_*.py')])
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
