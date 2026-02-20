"""FastAPI backend for NL2SQL.

Run:
    cd nl2sql_next && uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure nl2sql_next is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.nl2sql import Conversation, ask as ask_single
from core.schema import get_schema_context

app = FastAPI(title="NL2SQL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory conversation store ────────────────────────
_conversations: Dict[str, Conversation] = {}


def _get_conv(session_id: str) -> Conversation:
    if session_id not in _conversations:
        _conversations[session_id] = Conversation()
    return _conversations[session_id]


# ── Request/response models ─────────────────────────────

class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    model: Optional[str] = None  # e.g. "gpt-4.1", "gpt-5.2-low", "gpt-5.2-medium"


class AskResponse(BaseModel):
    session_id: str
    question: str
    mode: str  # "data_query" or "admin_assist"
    model: str  # model key used for this response
    sql: str
    columns: List[str]
    rows: List[List[Any]]
    answer: str  # admin_assist text answer (empty for data_query)
    error: Optional[str]
    retries: int
    elapsed_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_total: int = 0


class HistoryItem(BaseModel):
    question: str
    sql: str = ""
    answer: str = ""


# ── Routes ──────────────────────────────────────────────

@app.post("/api/ask", response_model=AskResponse)
def api_ask(req: AskRequest):
    """Ask a natural language question. Optionally pass session_id for multi-turn."""
    session_id = req.session_id or str(uuid.uuid4())
    conv = _get_conv(session_id)
    result = conv.ask(req.question, model_key=req.model)

    # Serialize Decimal/date values for JSON
    rows = _serialize_rows(result.get("rows", []))

    return AskResponse(
        session_id=session_id,
        question=result["question"],
        mode=result.get("mode", "data_query"),
        model=result.get("model", "gpt-4.1"),
        sql=result["sql"],
        columns=result.get("columns", []),
        rows=rows,
        answer=result.get("answer", ""),
        error=result.get("error"),
        retries=result.get("retries", 0),
        elapsed_ms=result.get("elapsed_ms", 0),
        tokens_in=result.get("tokens_in", 0),
        tokens_out=result.get("tokens_out", 0),
        tokens_total=result.get("tokens_total", 0),
    )


@app.get("/api/history/{session_id}", response_model=List[HistoryItem])
def api_history(session_id: str):
    """Get conversation history for a session."""
    if session_id not in _conversations:
        return []
    return [
        HistoryItem(
            question=h.get("question", ""),
            sql=h.get("sql", ""),
            answer=h.get("answer", ""),
        )
        for h in _conversations[session_id].history
    ]


@app.delete("/api/session/{session_id}")
def api_clear_session(session_id: str):
    """Clear a conversation session."""
    if session_id in _conversations:
        del _conversations[session_id]
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"status": "ok", "version": "0.1.0"}


# ── Helpers ─────────────────────────────────────────────

def _serialize_rows(rows: List[list]) -> List[List[Any]]:
    """Convert non-JSON-serializable values (Decimal, datetime) to primitives."""
    from decimal import Decimal
    from datetime import date, datetime

    def _conv(v: Any) -> Any:
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v

    return [[_conv(cell) for cell in row] for row in rows]
