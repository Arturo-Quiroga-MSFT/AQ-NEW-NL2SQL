from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import time
import uuid


class Flags(BaseModel):
    no_exec: bool = False
    no_reasoning: bool = False
    explain_only: bool = False
    refresh_schema: bool = False


class ExecutionResult(BaseModel):
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    preview: str = ""


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0
    total: int = 0


class PricingInfo(BaseModel):
    currency: str = "USD"
    input_per_1k: Optional[float] = None
    output_per_1k: Optional[float] = None
    source: str = "unset"


class GraphState(BaseModel):
    user_query: str = ""
    flags: Flags = Field(default_factory=Flags)

    schema_context: str = ""
    intent_entities: Any = None
    reasoning: str = ""
    sql_raw: str = ""
    sql_sanitized: str = ""
    execution_result: ExecutionResult = Field(default_factory=ExecutionResult)

    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    pricing: PricingInfo = Field(default_factory=PricingInfo)

    errors: List[str] = Field(default_factory=list)
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = Field(default_factory=lambda: time.time())

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
