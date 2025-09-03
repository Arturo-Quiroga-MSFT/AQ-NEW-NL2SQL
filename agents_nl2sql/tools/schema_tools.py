from __future__ import annotations
import os
import sys


def _ensure_repo_on_path() -> None:
    # allow running from repo root or elsewhere
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(pkg_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def get_schema_context() -> str:
    _ensure_repo_on_path()
    from schema_reader import get_sql_database_schema_context  # type: ignore
    return get_sql_database_schema_context()


def refresh_schema_cache() -> str:
    _ensure_repo_on_path()
    from schema_reader import refresh_schema_cache  # type: ignore
    return refresh_schema_cache()
