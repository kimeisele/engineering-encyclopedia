"""Build hook: carry the corpus (knowledge/, taxonomy/) inside the wheel.

The corpus lives at the repository root (CC BY 4.0, canonical copy). A
wheel built from this repository should carry it as package data so a user
in ANOTHER repository can `pip install .` and run `encyclopedia` without
setting ENCYCLOPEDIA_ROOT — the loader's resolution order 4. The copy is a
build artifact made at install time; the repository-root copies remain
canonical and are what tests and source checkouts use (resolution order 2).
"""

from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self) -> None:
        super().run()
        source = Path(__file__).resolve().parent
        dest = Path(self.build_lib) / "encyclopedia" / "data"
        for name in ("knowledge", "taxonomy"):
            src = source / name
            if not src.is_dir():
                continue
            dst = dest / name
            dst.mkdir(parents=True, exist_ok=True)
            for item in src.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(src)
                    target = dst / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(item.read_bytes())


setup(cmdclass={"build_py": BuildPy})
