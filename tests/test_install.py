import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_merge_multiline_and_preserve_nested_tables(self):
        source = '''model = "example"
[tui] # existing
status_line = [
 "model", # old
 "used-tokens",
]
screen_reader_detection_done = true
[tui.model_availability_nux]
example = 4
[features]
hooks = true
'''
        merged = installer.merge(source, {'status_line': ['git-branch'], 'notifications': True})
        parsed = tomllib.loads(merged)
        self.assertEqual(parsed['tui']['status_line'], ['git-branch'])
        self.assertTrue(parsed['tui']['screen_reader_detection_done'])
        self.assertEqual(parsed['tui']['model_availability_nux'], {'example': 4})
        self.assertIn('[features]\nhooks = true\n', merged)

    def test_missing_tui(self):
        self.assertEqual(tomllib.loads(installer.merge('[features]\nhooks = true\n', {'notifications': True})),
                         {'features': {'hooks': True}, 'tui': {'notifications': True}})

    def test_unsupported_layout_refused(self):
        with self.assertRaises(ValueError):
            installer.merge('tui = { notifications = false }\n', {'notifications': True})

    def test_install_and_guarded_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.toml'
            original = b'model = "example"\n[tui]\nscreen_reader_detection_done = true\n'
            config.write_bytes(original)
            config.chmod(0o640)
            command = [sys.executable, str(ROOT / 'install.py'), '--config', str(config)]
            dry = subprocess.run(command + ['--dry-run'], capture_output=True)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [config])
            run = subprocess.run(command, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            installed = config.read_bytes()
            backup, = Path(directory).glob('*.bak')
            self.assertEqual(backup.read_bytes(), original)
            self.assertEqual(config.stat().st_mode & 0o777, 0o640)
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            again = subprocess.run(command, capture_output=True)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(len(list(Path(directory).glob('*.bak'))), 1)
            config.write_bytes(installed + b'\n# later edit\n')
            refused = subprocess.run(command + ['--undo', str(backup)], capture_output=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertTrue(config.read_bytes().endswith(b'# later edit\n'))
            config.write_bytes(installed)
            backup.write_bytes(original + b'# changed backup\n')
            tampered = subprocess.run(command + ['--undo', str(backup)], capture_output=True)
            self.assertNotEqual(tampered.returncode, 0)
            self.assertEqual(config.read_bytes(), installed)
            backup.write_bytes(original)
            undo = subprocess.run(command + ['--undo', str(backup)], capture_output=True)
            self.assertEqual(undo.returncode, 0, undo.stderr)
            self.assertEqual(config.read_bytes(), original)

    def test_new_config_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'nested/config.toml'
            command = [sys.executable, str(ROOT / 'install.py'), '--config', str(config), '--preset', 'compact']
            subprocess.run(command, check=True, capture_output=True)
            backup, = config.parent.glob('*.bak')
            subprocess.run(command + ['--undo', str(backup)], check=True, capture_output=True)
            self.assertFalse(config.exists())

    def test_invalid_config_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.toml'
            config.write_text('[tui\n')
            run = subprocess.run([sys.executable, str(ROOT / 'install.py'), '--config', str(config)], capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(config.read_text(), '[tui\n')
            self.assertEqual(list(Path(directory).iterdir()), [config])


if __name__ == '__main__':
    unittest.main()
