from __future__ import annotations
import os
from typing import Tuple, List

REQUIRED_SQL_VARS = [
    "AZURE_SQL_SERVER",
    "AZURE_SQL_DB",
    "AZURE_SQL_USER",
    "AZURE_SQL_PASSWORD",
]

OPTIONAL_SQL_VARS = [
    "AZURE_SQL_ENCRYPT",
    "AZURE_SQL_TRUST_SERVER_CERTIFICATE",
]

def validate_sql_env() -> Tuple[bool, List[str]]:
    messages: List[str] = []
    ok = True
    for var in REQUIRED_SQL_VARS:
        val = os.getenv(var)
        if not val:
            ok = False
            messages.append(f"[MISSING] {var} is not set")
        else:
            messages.append(f"[OK] {var} present")
    for var in OPTIONAL_SQL_VARS:
        val = os.getenv(var)
        if val:
            messages.append(f"[OK-OPTIONAL] {var}={val}")
        else:
            messages.append(f"[INFO] {var} not set (optional)")
    return ok, messages

__all__ = ["validate_sql_env"]