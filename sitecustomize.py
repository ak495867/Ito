"""Auto-imported at interpreter startup.

Puts this repo's source directories on sys.path so tests (run via pytest,
`python -m unittest`, or `python -m unittest discover`) can import modules
by bare name. The source dirs are flat, not installed packages, so plain
imports from the repo root cannot reach them.

pytest also loads conftest.py (tests/python/conftest.py); this covers the
unittest path, which ignores conftest.py entirely.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_PATHS = (
    ROOT / "python" / "connectivity",
    ROOT / "python" / "operations",
    ROOT / "python" / "ops_tools",
    ROOT / "python" / "reconciliation",
    ROOT / "python" / "replay",
    ROOT / "python" / "backtest",
    ROOT / "python" / "portfolio",
    ROOT / "scripts",
    ROOT / "scripts" / "operations",
)

for _path in _PATHS:
    _str = str(_path)
    if _str not in sys.path:
        sys.path.insert(0, _str)