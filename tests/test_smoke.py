"""Bootstrap smoke test: the package imports and the repository layout exists."""

import unittest
from pathlib import Path

import encyclopedia


class TestSmoke(unittest.TestCase):
    def test_package_imports(self):
        self.assertTrue(encyclopedia.__version__)

    def test_repo_layout_present(self):
        root = Path(encyclopedia.__file__).resolve().parents[2]
        self.assertTrue((root / "knowledge").is_dir())
        self.assertTrue((root / "LICENSE").is_file())
        self.assertTrue((root / "AGENTS.md").is_file())


if __name__ == "__main__":
    unittest.main()
