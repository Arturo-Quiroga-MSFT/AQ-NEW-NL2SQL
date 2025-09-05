from __future__ import annotations
import os
import json
from typing import Any, Dict, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables early so AZURE_OPENAI_* are available
load_dotenv()


# Azure OpenAI configuration from environment
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

# Unified maximum completion tokens for all stages (can be overridden via env)
MAX_COMPLETION_TOKENS = int(os.getenv("MAX_COMPLETION_TOKENS", "8192"))


def azure_chat_completions(messages: list[dict[str, Any]], max_completion_tokens: int | None = None) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Reasoning-safe direct Chat Completions call for GPT-5/o-series (no temperature/top_p).

    Returns (content, usage_dict)
    """
    import requests

    if not ENDPOINT or not DEPLOYMENT_NAME or not API_KEY:
        raise RuntimeError("Missing AZURE_OPENAI_* environment variables for Chat Completions.")

    url = f"{ENDPOINT.rstrip('/')}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"
    payload: Dict[str, Any] = {"messages": messages}
    # Apply unified default if not explicitly provided
    payload["max_completion_tokens"] = max_completion_tokens if max_completion_tokens is not None else MAX_COMPLETION_TOKENS
    headers = {"api-key": API_KEY, "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage")
    return content, usage


def accumulate_usage(token_usage: Optional[Dict[str, Any]], agg: Dict[str, int]) -> Dict[str, int]:
    """Accumulate usage dict into an aggregate usage object with keys: prompt, completion, total.

    Returns the updated aggregate mapping.
    """
    if not token_usage:
        return agg
    agg["prompt"] = int(agg.get("prompt", 0)) + int(token_usage.get("prompt_tokens", 0) or 0)
    agg["completion"] = int(agg.get("completion", 0)) + int(token_usage.get("completion_tokens", 0) or 0)
    if "total_tokens" in token_usage and token_usage.get("total_tokens") is not None:
        agg["total"] = int(agg.get("total", 0)) + int(token_usage.get("total_tokens", 0) or 0)
    else:
        agg["total"] = int(agg.get("total", 0)) + (
            int(token_usage.get("prompt_tokens", 0) or 0) + int(token_usage.get("completion_tokens", 0) or 0)
        )
    return agg


# Pricing helpers (USD/CAD) adapted from main pipeline
def _normalize_dep_to_env_key(name: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9]+", "_", (name or "")).upper().strip("_")


def _load_pricing_config() -> Dict[str, Dict[str, Any]]:
    try:
        repo_root = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(repo_root, "azure_openai_pricing.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _get_target_currency() -> str:
    cur = (os.getenv("AZURE_OPENAI_PRICE_CURRENCY", "USD") or "USD").upper()
    return cur if cur in ("USD", "CAD") else "USD"


def _convert_currency(amount: float, from_currency: str, to_currency: str) -> Optional[float]:
    if from_currency == to_currency:
        return amount
    if from_currency == "USD" and to_currency == "CAD":
        rate = os.getenv("AZURE_OPENAI_PRICE_USD_TO_CAD")
        if rate:
            try:
                return amount * float(rate)
            except ValueError:
                return None
    if from_currency == "CAD" and to_currency == "USD":
        rate = os.getenv("AZURE_OPENAI_PRICE_CAD_TO_USD")
        if rate:
            try:
                return amount * float(rate)
            except ValueError:
                return None
    return None


def get_pricing_for_deployment(dep_name: Optional[str]) -> tuple[Optional[float], Optional[float], str, str]:
    dep = dep_name or ""
    dep_key = _normalize_dep_to_env_key(dep)
    target_cur = _get_target_currency()
    # 1) Deployment-specific env
    in_env = os.getenv(f"AZURE_OPENAI_PRICE_{dep_key}_INPUT_PER_1K")
    out_env = os.getenv(f"AZURE_OPENAI_PRICE_{dep_key}_OUTPUT_PER_1K")
    if in_env and out_env:
        try:
            return float(in_env), float(out_env), f"env:{dep_key}", target_cur
        except ValueError:
            pass
    # 2) Global env
    in_glob = os.getenv("AZURE_OPENAI_PRICE_INPUT_PER_1K")
    out_glob = os.getenv("AZURE_OPENAI_PRICE_OUTPUT_PER_1K")
    if in_glob and out_glob:
        try:
            return float(in_glob), float(out_glob), "env:global", target_cur
        except ValueError:
            pass
    # 3) File
    pricing_map = _load_pricing_config()
    if pricing_map:
        entry = pricing_map.get(dep.lower()) or pricing_map.get(dep)
        if entry and isinstance(entry, dict):
            if "input_per_1k" in entry and "output_per_1k" in entry:
                try:
                    in_usd = float(entry.get("input_per_1k"))
                    out_usd = float(entry.get("output_per_1k"))
                    if target_cur == "USD":
                        return in_usd, out_usd, "file:azure_openai_pricing.json", "USD"
                    in_cad = _convert_currency(in_usd, "USD", target_cur)
                    out_cad = _convert_currency(out_usd, "USD", target_cur)
                    if in_cad is not None and out_cad is not None:
                        return in_cad, out_cad, "file:azure_openai_pricing.json (converted)", target_cur
                    return in_usd, out_usd, "file:azure_openai_pricing.json (USD; no conversion)", "USD"
                except Exception:
                    pass
            cur_block = entry.get(target_cur)
            if isinstance(cur_block, dict) and "input_per_1k" in cur_block and "output_per_1k" in cur_block:
                try:
                    return float(cur_block["input_per_1k"]), float(cur_block["output_per_1k"]), "file:azure_openai_pricing.json", target_cur
                except Exception:
                    pass
            usd_block = entry.get("USD")
            if isinstance(usd_block, dict) and "input_per_1k" in usd_block and "output_per_1k" in usd_block:
                try:
                    in_usd = float(usd_block["input_per_1k"])
                    out_usd = float(usd_block["output_per_1k"])
                    if target_cur == "USD":
                        return in_usd, out_usd, "file:azure_openai_pricing.json", "USD"
                    in_conv = _convert_currency(in_usd, "USD", target_cur)
                    out_conv = _convert_currency(out_usd, "USD", target_cur)
                    if in_conv is not None and out_conv is not None:
                        return in_conv, out_conv, "file:azure_openai_pricing.json (converted)", target_cur
                    return in_usd, out_usd, "file:azure_openai_pricing.json (USD; no conversion)", "USD"
                except Exception:
                    pass
    return None, None, "unset", target_cur
