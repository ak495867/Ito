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
    path_str = str(root / relative_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
