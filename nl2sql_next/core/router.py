"""Intent router — classifies user questions into pipeline modes.

Modes:
- data_query: needs SQL generation + execution (existing NL2SQL pipeline)
- admin_assist: schema/admin/advice question answered directly from context
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from openai import AzureOpenAI
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

MODES = ("data_query", "admin_assist")

ROUTER_PROMPT = """\
You are a question classifier for a database assistant.

Classify the user's question into exactly one of these categories:

data_query — The user wants to retrieve, analyze, or compute something FROM the data.
  Examples: "top 5 products by revenue", "monthly sales trend", "how many orders last week",
  "average order value by store", "compare Q1 vs Q2", "which customers returned the most"

admin_assist — The user is asking ABOUT the database itself, its schema, design, or wants
  advice on database management, optimization, indexing, or general explanations.
  ALSO use this category for any DATA MODIFICATION request: INSERT, UPDATE, DELETE,
  adding rows, removing rows, changing values, or any write operation.
  Examples: "what tables are in the database?", "describe the DimCustomer table",
  "how are orders related to products?", "what indexes should I add?",
  "explain the star schema", "what's the partition key?", "how many columns in FactOrders?",
  "suggest improvements to the schema", "what are best practices for this schema?",
  "delete the Cryptocurrency payment method", "add a new store", "insert a row",
  "update customer 5's email", "remove the test product"

Respond with ONLY the category name: data_query or admin_assist
"""


_client: Optional[AzureOpenAI] = None


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
        )
    return _client


def classify(question: str) -> Tuple[str, Dict[str, int]]:
    """Classify a question into a pipeline mode.

    Returns (mode, usage_dict).
    """
    client = _get_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

    resp = client.responses.create(
        model=deployment,
        instructions=ROUTER_PROMPT,
        input=question,
        temperature=0,
        max_output_tokens=20,
    )
    raw = (resp.output_text or "").strip().lower()

    usage: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    if resp.usage:
        usage["input_tokens"] = getattr(resp.usage, "input_tokens", 0)
        usage["output_tokens"] = getattr(resp.usage, "output_tokens", 0)
        usage["total_tokens"] = getattr(resp.usage, "total_tokens", 0)

    # Parse — be lenient
    for mode in MODES:
        if mode in raw:
            return mode, usage
    return "data_query", usage  # default to SQL pipeline
