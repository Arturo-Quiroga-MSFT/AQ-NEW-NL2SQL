"""GraphState and supporting models for the NL2SQL pipeline."""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Flags(BaseModel):
    no_exec: bool = False
    explain_only: bool = False
    refresh_schema: bool = False


class ExecutionResult(BaseModel):
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    preview: str = ""


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0
    total: int = 0


class GraphState(BaseModel):
    user_query: str = ""
    flags: Flags = Field(default_factory=Flags)
    question_category: str = "Easy"

    schema_context: str = ""
    intent_entities: Any = None
    intent_raw_response: str = ""
    sql_raw: str = ""
    sql_sanitized: str = ""
    execution_result: ExecutionResult = Field(default_factory=ExecutionResult)

    # Per-stage token caps (None → use global default)
    intent_max_tokens: int | None = None
    sql_max_tokens: int | None = None

    # Environment validation
    azure_env_valid: bool = True
    azure_env_messages: list[str] = Field(default_factory=list)
    sql_env_valid: bool = True
    sql_env_messages: list[str] = Field(default_factory=list)

    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    errors: List[str] = Field(default_factory=list)
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = Field(default_factory=lambda: time.time())

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
