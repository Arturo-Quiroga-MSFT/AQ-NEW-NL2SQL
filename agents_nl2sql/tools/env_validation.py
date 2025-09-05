from __future__ import annotations
import os
from typing import Tuple, List

REQUIRED_VARS = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
]

OPTIONAL_VARS = [
    "AZURE_OPENAI_API_VERSION",
]

def validate_azure_openai_env() -> Tuple[bool, List[str]]:
    messages: List[str] = []
    ok = True
    for var in REQUIRED_VARS:
        val = os.getenv(var)
        if not val:
            ok = False
            messages.append(f"[MISSING] {var} is not set")
        else:
            if var == "AZURE_OPENAI_ENDPOINT" and not val.lower().startswith("http"):
                ok = False
                messages.append(f"[INVALID] {var} does not look like a URL: {val}")
            else:
                messages.append(f"[OK] {var} present")
    for var in OPTIONAL_VARS:
        val = os.getenv(var)
        if val:
            messages.append(f"[OK-OPTIONAL] {var} present ({val})")
        else:
            messages.append(f"[INFO] {var} not set; using library default")
    return ok, messages

__all__ = ["validate_azure_openai_env"]