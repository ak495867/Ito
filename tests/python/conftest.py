import sys
from pathlib import Path

root = Path(__file__).parents[2]
for relative_path in (
    "python/connectivity",
    "python/operations",
    "python/ops_tools",
    "python/reconciliation",
    "python/replay",
    "python/backtest",
    "python/portfolio",
    "scripts",
    "scripts/operations",
):
    sys.path.insert(0, str(root / relative_path))