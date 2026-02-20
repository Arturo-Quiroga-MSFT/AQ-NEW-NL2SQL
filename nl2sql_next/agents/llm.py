"""Azure OpenAI Chat Completions helper."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
MAX_COMPLETION_TOKENS = int(os.getenv("MAX_COMPLETION_TOKENS", "8192"))


def azure_chat_completions(
    messages: list[dict[str, Any]],
    max_completion_tokens: int | None = None,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Call Azure OpenAI Chat Completions. Returns (content, usage_dict)."""
    if not ENDPOINT or not DEPLOYMENT_NAME or not API_KEY:
        raise RuntimeError("Missing AZURE_OPENAI_* environment variables.")

    url = (
        f"{ENDPOINT.rstrip('/')}/openai/deployments/{DEPLOYMENT_NAME}"
        f"/chat/completions?api-version={API_VERSION}"
    )
    payload: Dict[str, Any] = {
        "messages": messages,
        "max_completion_tokens": max_completion_tokens or MAX_COMPLETION_TOKENS,
    }
    headers = {"api-key": API_KEY, "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage")
    return content, usage


def accumulate_usage(
    token_usage: Optional[Dict[str, Any]], agg: Dict[str, int]
) -> Dict[str, int]:
    """Accumulate token usage into aggregate dict."""
    if not token_usage:
        return agg
    agg["prompt"] = agg.get("prompt", 0) + int(token_usage.get("prompt_tokens", 0) or 0)
    agg["completion"] = agg.get("completion", 0) + int(
        token_usage.get("completion_tokens", 0) or 0
    )
    agg["total"] = agg.get("total", 0) + int(token_usage.get("total_tokens", 0) or 0)
    if not agg["total"]:
        agg["total"] = agg["prompt"] + agg["completion"]
    return agg
