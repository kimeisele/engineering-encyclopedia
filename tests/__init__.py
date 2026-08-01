"""Test suite for engineering-encyclopedia.

Package marker so `python -m unittest discover` recurses into tests/.
Also puts src/ on sys.path so the required command works out of the box
without a prior `pip install` (CI installs the package and is unaffected).
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
