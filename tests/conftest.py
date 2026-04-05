import sys
from pathlib import Path


# Ensure local package imports work even when pytest is invoked from the parent
# workspace instead of from the repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
