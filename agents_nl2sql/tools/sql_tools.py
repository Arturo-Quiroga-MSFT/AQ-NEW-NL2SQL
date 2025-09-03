from __future__ import annotations
import os
import sys
from typing import List, Dict, Any


def _ensure_repo_on_path() -> None:
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(pkg_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def execute_sql_query(sql: str) -> List[Dict[str, Any]]:
    _ensure_repo_on_path()
    from sql_executor import execute_sql_query as run  # type: ignore
    return run(sql)
