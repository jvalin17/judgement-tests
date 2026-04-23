"""
Root conftest for judgement-tests.

Adds the main judgement repo to sys.path so backend tests can import
from backend.app.* as usual. Expects the main repo to be cloned as a
sibling directory (../judgement) or provided via JUDGEMENT_REPO env var.
"""
import os
import sys
from pathlib import Path

# Resolve main repo path
repo_env = os.environ.get("JUDGEMENT_REPO")
if repo_env:
    main_repo = Path(repo_env).resolve()
else:
    # Default: sibling directory
    main_repo = Path(__file__).resolve().parent.parent / "judgement"

if not (main_repo / "backend").is_dir():
    raise RuntimeError(
        f"Cannot find judgement repo at {main_repo}. "
        "Set JUDGEMENT_REPO env var to the repo root."
    )

# Add main repo root to sys.path so 'backend.app.*' imports work
if str(main_repo) not in sys.path:
    sys.path.insert(0, str(main_repo))
