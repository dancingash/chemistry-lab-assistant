"""Exercise pip's real --python handoff offline, including Unicode diagnostics."""
from contextlib import redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import venv
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from install import install_dependencies
from lab_config import python_executable


@unittest.skipUnless(importlib.util.find_spec('pip'), 'Installer Python needs pip')
class PipEncodingTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name) / 'CI skills 中文'
        self.folder.mkdir()
        self.runtime = python_executable(self.folder / 'lab-rd')
        venv.EnvBuilder(with_pip=False).create(self.runtime.parent.parent)
        self.requirements = self.folder / 'requirements.lock'
        self.environment = patch.dict(os.environ, {
            'PYTHONIOENCODING': 'cp1252', 'PYTHONUTF8': '0',
            'PYTHONLEGACYWINDOWSSTDIO': '1', 'PIP_CONFIG_FILE': os.devnull,
            'PIP_NO_INDEX': '1', 'PIP_NO_INPUT': '1',
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_real_pip_installs_local_wheel_into_environment_without_pip(self):
        wheel = self.folder / 'lab_rd_encoding_fixture-1.0-py3-none-any.whl'
        metadata = 'lab_rd_encoding_fixture-1.0.dist-info/'
        with ZipFile(wheel, 'w') as archive:
            archive.writestr('lab_rd_encoding_fixture.py', "VALUE = '中文'\n")
            archive.writestr(metadata + 'METADATA',
                             'Metadata-Version: 2.1\nName: lab-rd-encoding-fixture\nVersion: 1.0\n')
            archive.writestr(metadata + 'WHEEL',
                             'Wheel-Version: 1.0\nGenerator: lab-rd-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
            archive.writestr(metadata + 'RECORD', '')
        self.requirements.write_text(str(wheel) + '\n', encoding='utf-8')
        output = io.StringIO()
        with redirect_stdout(output):
            install_dependencies(self.runtime, self.requirements)
        self.assertIn('中文', output.getvalue())
        self.assertNotIn('UnicodeEncodeError', output.getvalue())
        result = subprocess.run([str(self.runtime), '-c',
                                 'import importlib.util, lab_rd_encoding_fixture as fixture; '
                                 'assert fixture.VALUE == "\\u4e2d\\u6587"; '
                                 'assert importlib.util.find_spec("pip") is None'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_pip_failure_preserves_unicode_diagnostics_and_exit_code(self):
        missing = self.folder / '不存在' / 'missing-1.0-py3-none-any.whl'
        self.requirements.write_text(str(missing) + '\n', encoding='utf-8')
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(subprocess.CalledProcessError) as failure:
            install_dependencies(self.runtime, self.requirements)
        self.assertEqual(failure.exception.returncode, 1)
        self.assertIn('不存在', output.getvalue())
        self.assertIn('ERROR', output.getvalue())
        self.assertNotIn('UnicodeEncodeError', output.getvalue())


if __name__ == '__main__':
    unittest.main()
