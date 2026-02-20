"""Environment validation helpers."""
from __future__ import annotations

import os
from typing import List, Tuple


def validate_azure_openai_env() -> Tuple[bool, List[str]]:
    msgs: List[str] = []
    ok = True
    for var in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT_NAME"):
        val = os.getenv(var)
        if not val:
            ok = False
            msgs.append(f"[MISSING] {var}")
        else:
            msgs.append(f"[OK] {var}")
    return ok, msgs


def validate_sql_env() -> Tuple[bool, List[str]]:
    msgs: List[str] = []
    ok = True
    for var in ("AZURE_SQL_SERVER", "AZURE_SQL_DB"):
        val = os.getenv(var)
        if not val:
            ok = False
            msgs.append(f"[MISSING] {var}")
        else:
            msgs.append(f"[OK] {var}")
    auth = os.getenv("AZURE_SQL_AUTH", "entra").lower()
    msgs.append(f"[OK] Auth mode: {auth}")
    if auth != "entra":
        for var in ("AZURE_SQL_USER", "AZURE_SQL_PASSWORD"):
            if not os.getenv(var):
                ok = False
                msgs.append(f"[MISSING] {var}")
    return ok, msgs
